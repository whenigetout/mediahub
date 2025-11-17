# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
# pipelines.py  (replace or add this pipeline)
import sys
from pathlib import Path
from itemadapter import ItemAdapter
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import json
import logging

log = logging.getLogger(__name__)

# ---- Make the mediahub backend importable from inside scrapy ----
# Adjust how many parents to go up depending on where your scrapy project sits.
# This will add the repo root so `backend.db.models` can be imported.
HERE = Path(__file__).resolve()
# example layout from your tree: <repo-root>/app/scrapers/jav/... and <repo-root>/backend/db/models.py
# So we go up 4 parents to reach repo root; adjust if needed.
REPO_ROOT = HERE.parents[4]     # <-- change this number if your layout differs
sys.path.insert(0, str(REPO_ROOT / "backend"))  # add backend on path

# Now import your SQLAlchemy models/engine
try:
    from db.models import JavMetadata, engine, Base   # your models file creates engine & tables
except Exception as e:
    log.exception("Failed to import db.models — check sys.path and REPO_ROOT. %s", e)
    raise

# Prepare a Session factory
Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class SQLAlchemyPipeline:
    def open_spider(self, spider):
        # optional: ensure tables exist (models.py already runs create_all on import).
        # Base.metadata.create_all(bind=engine)
        self.session = Session()

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        # get code (consistent with your spider)
        code = adapter.get("code") or adapter.get("jav_code") or adapter.get("id")
        if not code:
            spider.logger.warning("Item without code — skipping: %r", dict(item))
            return item

        # prepare a JavMetadata instance (use fields you have in models)
        # store full metadata in metadata_json (or metadata_json field name you use)
        metadata_obj = dict(item)
        # guard: ensure JSON-serializable if your model expects JSON; keep it simple and dump to string if needed
        try:
            # If JavMetadata.metadata_json is JSON type in SQLAlchemy, we can pass dict directly.
            jm = JavMetadata(
                code=code,
                metadata_json=metadata_obj,
                source_url=metadata_obj.get("movie_url") or metadata_obj.get("url"),
            )
            # upsert: merge will INSERT or UPDATE based on PK
            self.session.merge(jm)
            self.session.commit()
        except SQLAlchemyError as e:
            spider.logger.exception("DB error writing code %s: %s", code, e)
            try:
                self.session.rollback()
            except Exception:
                pass
        except Exception as e:
            spider.logger.exception("Unexpected error in pipeline for code %s: %s", code, e)

        return item

    def close_spider(self, spider):
        try:
            self.session.commit()
        except Exception:
            pass
        finally:
            self.session.close()

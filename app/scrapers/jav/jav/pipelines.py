# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
import json, sqlite3
from pathlib import Path

class JavPipeline:
    def process_item(self, item, spider):
        return item

DB_PATH = Path("jav_metadata.db")

class SQLitePipeline:
    def open_spider(self, spider):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        # single connection for the pipeline lifetime
        # timeout=30 allows the connection to wait if briefly locked
        self.conn = sqlite3.connect(str(DB_PATH), timeout=30, check_same_thread=False)
        self.cur = self.conn.cursor()
        # create table if missing
        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS jav (
            code TEXT PRIMARY KEY,
            metadata_json TEXT,
            url TEXT,
            status TEXT,
            note TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        self.conn.commit()

        # prepare an upsert SQL (faster than formatting each time)
        self._upsert_sql = """
        INSERT INTO jav(code, metadata_json, url, status, note)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(code) DO UPDATE SET
            metadata_json=excluded.metadata_json,
            url=excluded.url,
            status=excluded.status,
            note=excluded.note,
            updated_at=CURRENT_TIMESTAMP
        """

    def process_item(self, item, spider):
        metadata = dict(item)
        code = metadata.get("code") or metadata.get("jav_code")
        url = metadata.get("movie_url", "")
        status = metadata.get("status", "ok")  # default to 'ok' if not present
        note = metadata.get("note", "")  # default to 'ok' if not present

        if not code:
            spider.logger.warning("Skipping item without code: %r", metadata)
            return item

        metadata_json = json.dumps(metadata, ensure_ascii=False)
        self.cur.execute(self._upsert_sql, (code, metadata_json, url, status, note))
        # commit every N items might be faster; commit per item is safest
        self.conn.commit()
        return item

    def close_spider(self, spider):
        self.conn.commit()
        self.conn.close()
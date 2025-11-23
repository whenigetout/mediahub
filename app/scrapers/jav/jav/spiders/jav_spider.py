import scrapy, json, re
class JAVSpider(scrapy.Spider):
    name = "jav"

    # put many codes here
    with open("jav/jav_codes.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    jav_codes = [obj["jav_code"] for obj in data]

    def start_requests(self):
        for code in self.jav_codes:
            search_url = f"https://javfilms.com/search?keywords={code}"
            # pass the code through meta so parse() knows which one this is
            yield scrapy.Request(search_url, callback=self.parse, meta={"jav_code": code})


    def extract_actresses_from_response(self, response):
        """
        Return a list of actress dicts extracted from the videodetailbox -> videopictures block.
        """
        actresses = []

        # selector for each actress block (each anchor contains one actress card)
        actor_nodes = response.xpath("//div[contains(@class,'videodetailbox')]//div[contains(@class,'videopictures')]//a")

        for node in actor_nodes:
            # profile href (relative -> make absolute)
            href = node.xpath("./@href").get()
            profile_href = response.urljoin(href) if href else None

            # name: usually the first <strong> under the actor card
            name = node.xpath(".//strong[1]/normalize-space(text())").get()
            if name:
                name = name.strip()

            # photo url is inside <span style="background-image:url('...')">
            style = node.xpath(".//span/@style").get() or ""
            m = re.search(r"""url\(['"]?(.*?)['"]?\)""", style)
            photo = m.group(1) if m else None
            photo_url = response.urljoin(photo) if photo else None

            # helper to get the text following a <strong>Label:</strong>
            def field_value(label):
                # finds a div that has a <strong> with the exact label then grabs the remaining text nodes in that div
                txt_nodes = node.xpath(f".//div[strong[normalize-space(.)='{label}']]/text()").getall()
                # join and clean whitespace
                txt = " ".join([t.strip() for t in txt_nodes if t and t.strip()])
                # treat '-' or empty as None
                if not txt or txt.strip() in {"-", "—"}:
                    return None
                return txt

            birthday     = field_value("Birthday:")
            cup_size     = field_value("Cup Size:")
            height       = field_value("Height:")
            measurements = field_value("Measurements:")
            blood_type   = field_value("Blood Type:")

            actresses.append({
                "name": name,
                "profile_href": profile_href,
                "photo_url": photo_url,
                "birthday": birthday,
                "cup_size": cup_size,
                "height": height,
                "measurements": measurements,
                "blood_type": blood_type,
            })

        return actresses


    def parse_video_metadata(self, response):
        jav_code = response.meta.get("jav_code")
        movie_url = response.meta.get("movie_url")
        panel = response.xpath("//div[@id='videodetails']")

        def text_after_label(label):
            node = panel.xpath(f".//h3[normalize-space(.)='{label}']/following-sibling::p[1]")
            if not node:
                return None
            # join all text pieces and normalize whitespace
            txt = "".join(node.xpath(".//text()").getall()).strip()
            return " ".join(txt.split())

        def first_link_after_label(label):
            node = panel.xpath(f".//h3[normalize-space(.)='{label}']/following-sibling::p[1]//a[1]")
            if not node:
                return None, None
            text = node.xpath("normalize-space(text())").get()
            href = node.xpath("./@href").get()
            return text, response.urljoin(href) if href else None

        metadata = {}

        # JAV code
        metadata["code"] = jav_code

        # URL
        metadata["movie_url"] = movie_url

        # Release Date
        metadata["release_date"] = text_after_label("Release Date")  # e.g. "8 Nov, 2025"

        # Video poster
        metadata["movie_poster_url"] = response.xpath("//img[@id='videoplayerplaceholder']/@src").get()

        # Video title
        metadata["movie_title"] = response.xpath("//h1[@id='vidtitle']/text()").get()

        # Movie Length
        # may contain extra labels like "Very Long" — you'll probably want just the minutes number
        raw_length = text_after_label("Movie Length")
        metadata["movie_length_raw"] = raw_length
        # optional: extract number minutes
        import re
        m = re.search(r"(\d+)\s*minutes", raw_length or "", re.I)
        metadata["movie_length_minutes"] = int(m.group(1)) if m else None

        # Studio / Producer (name + link)
        name, href = first_link_after_label("Studio / Producer")
        metadata["studio_name"] = name
        metadata["studio_href"] = href

        # Played
        played = text_after_label("Played")  # e.g. "422 times"
        metadata["played_raw"] = played
        m = re.search(r"(\d+)", played or "")
        metadata["played_count"] = int(m.group(1)) if m else None

        # Popularity Ranking
        pop = text_after_label("Popularity Ranking")  # e.g. "43384 / 535895"
        metadata["popularity_raw"] = pop
        if pop:
            p = re.findall(r"(\d+)", pop)
            if len(p) >= 2:
                metadata["pop_rank"] = int(p[0])
                metadata["pop_total"] = int(p[1])

        # Other names (comma separated <i> elements)
        other_names_node = panel.xpath(".//h3[normalize-space(.)='Other Names']/following-sibling::p[1]")
        other_names = [x.strip() for x in other_names_node.xpath(".//i/text()").getall()] if other_names_node else []
        metadata["other_names"] = other_names

        # Total Actresses
        total_act = text_after_label("Total Actresses")
        metadata["total_actresses_raw"] = total_act
        m = re.search(r"(\d+)", total_act or "")
        metadata["total_actresses"] = int(m.group(1)) if m else None

        # Actress Body Type (comma separated)
        body_type = text_after_label("Actress Body Type")
        metadata["actress_body_type"] = [t.strip() for t in (body_type or "").split(",") if t.strip()]

        # Uncensored (Yes/No)
        metadata["uncensored"] = text_after_label("Uncensored")

        # Language
        metadata["language"] = text_after_label("Language")

        # Subtitles
        metadata["subtitles"] = text_after_label("Subtitles")

        # Copyright Owner
        metadata["copyright_owner"] = text_after_label("Copyright Owner")

        # Tags/Categories
        tags_a_nodes = response.xpath("//div[h2='Categories']//a")
        tags = []
        for a_tag in tags_a_nodes:
            tag_name = a_tag.xpath("./button/text()").get()
            # tag_link_url = "https://javfilms.com/" + a_tag.xpath("./@href").get()
            tag_link_url = response.urljoin(a_tag.xpath("./@href").get())

            tag = {
                "tag_name": tag_name,
                "tag_link_url": tag_link_url
            }

            tags.append(tag)

        metadata["tags"] = tags

        # Actresses
        actresses = []

        # selector for each actress block (each anchor contains one actress card)
        # multiple actresses
        videopicturebox_node = response.xpath(
            "//div[contains(@class, 'videopictures')]//div[strong='Birthday:']//ancestor::div[contains(@class,'videopictures')]"
            )
        
        if videopicturebox_node:

            actress_nodes = videopicturebox_node.xpath(".//a")

            for actress_a_tag in actress_nodes:
                actress = {}

                # actress_page_url = "https://javfilms.com/" + actress_a_tag.xpath("./@href").get()
                actress_page_url = response.urljoin(actress_a_tag.xpath("./@href").get())
                actress["actress_page_url"] = actress_page_url

                # photo url is inside <span style="background-image:url('...')">
                style = actress_a_tag.xpath(".//span/@style").get() or ""
                m = re.search(r"""url\(['"]?(.*?)['"]?\)""", style)
                photo = m.group(1) if m else None
                photo_url = response.urljoin(photo) if photo else None
                actress["photo_url"] = photo_url

                name = actress_a_tag.xpath("normalize-space((.//strong)[1])").get()
                actress["name"] = name

                birthday = actress_a_tag.xpath("normalize-space(.//div[strong='Birthday:']/text())").get()
                actress["birthday"] = birthday

                cupsize = actress_a_tag.xpath("normalize-space(.//div[strong='Cup Size:']/text())").get()
                actress["cupsize"] = cupsize

                height = actress_a_tag.xpath("normalize-space(.//div[strong='Height:']/text())").get()
                actress["height"] = height

                measurements = actress_a_tag.xpath("normalize-space(.//div[strong='Measurements:']/text())").get()
                actress["measurements"] = measurements

                bloodtype = actress_a_tag.xpath("normalize-space(.//div[strong='Blood Type:']/text())").get()
                actress["bloodtype"] = bloodtype

                actresses.append(actress)
        
        # single featured actress
        else:
            featured_actress_div = response.xpath("//div[./h2[contains(normalize-space(.), 'Featured Actress')]]")

            actress_detail_labels = featured_actress_div.xpath(".//strong")

            actress = {}
            actress_page_url = response.urljoin(featured_actress_div.xpath(".//h2//a/@href").get())
            actress["actress_page_url"] = actress_page_url

            # photo url is inside <span style="background-image:url('...')">
            style = featured_actress_div.xpath(".//span/@style").get() or ""
            m = re.search(r"""url\(['"]?(.*?)['"]?\)""", style)
            photo = m.group(1) if m else None
            photo_url = response.urljoin(photo) if photo else None
            actress["photo_url"] = photo_url

            for node in actress_detail_labels:
                
                key = node.xpath("./text()").get().strip()
                value = node.xpath("./../text()").get()

                actress[key] = value
                
            actresses.append(actress)

        metadata["actresses"] = actresses

        # with open("jav_metadata.json", "w") as f:
        #     json.dump(metadata, f, indent=4)

        yield metadata

        # return metadata

    def parse(self, response):
        jav_code = response.meta.get("jav_code")  # code for this request
        href = response.xpath(
            f"//strong[normalize-space(.)='{jav_code}']/ancestor::a[1]/@href"
        ).get()

        if not href:
            self.logger.warning("No result for %s", jav_code)
            yield {
                "code": jav_code,
                "url": "",
                "status": "not_found",
                "note": "page returned 404 or selector missing"
            }


            return

        jav_page_link = jav_page_link = response.urljoin(href)

        yield response.follow(jav_page_link, callback=self.parse_video_metadata, meta={"jav_code": jav_code, "movie_url": jav_page_link})

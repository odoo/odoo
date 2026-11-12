import logging

from odoo import api, models
from odoo.exceptions import UserError
from odoo.tools.json import scriptsafe as json_safe

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Blog hub ("News & Events")
#
# The website exposes a single blog used as a hub: /blog.  Posts are separated
# by tag (News / Events / Articles) instead of by blog, so the homepage can
# pull "News Update" and "Events Update" from the very same blog.
# ---------------------------------------------------------------------------

BLOG_NAME = {"en_US": "News & Events", "th_TH": "ข่าวและกิจกรรม"}
BLOG_SUBTITLE = {
    "en_US": "Product launches, project milestones, exhibitions and technical articles.",
    "th_TH": "ข่าวผลิตภัณฑ์ใหม่ ความสำเร็จของโครงการ งานแสดงสินค้า และบทความทางเทคนิค",
}
BLOG_INTRO = {
    "en_US": "<p>Stay up to date with what is happening at The Auto-Info Co., Ltd. — "
             "new products, delivered projects, exhibitions and hands-on technical articles "
             "from our engineering teams.</p>",
    "th_TH": "<p>ติดตามความเคลื่อนไหวของบริษัท ออโต้-อินโฟ จำกัด — สินค้าใหม่ โครงการที่ส่งมอบแล้ว "
             "งานแสดงสินค้า และบทความทางเทคนิคจากทีมวิศวกรของเรา</p>",
}

TAG_CATEGORY_NAME = {"en_US": "Topics", "th_TH": "หมวดหมู่"}

# Branded cover of the /blog hub (and of every post page).  It replaces the
# stock Odoo demo cover so the hub blends with the rest of the website.
BLOG_COVER = {
    "background_color_class": "o_cc3",
    "background-image": "url(/od19_website/static/src/img/hero/industrial.jpg)",
    "opacity": "0.45",
    "resize_class": "o_half_screen_height o_record_has_cover",
}

# (xmlid suffix, colour index, {lang: name})
TAGS = [
    ("blog_tag_news", 0, {"en_US": "News", "th_TH": "ข่าวสาร"}),
    ("blog_tag_events", 1, {"en_US": "Events", "th_TH": "กิจกรรม"}),
    ("blog_tag_articles", 2, {"en_US": "Articles", "th_TH": "บทความ"}),
]

# (tag xmlid suffix, post_date, {lang: title}, {lang: subtitle}, {lang: html})
_POSTS = [
    (
        "blog_tag_news",
        "2026-04-18 09:00:00",
        {"en_US": "Auto-Info renews ISO 9001:2015 certification",
         "th_TH": "ออโต้-อินโฟ ต่ออายุการรับรอง ISO 9001:2015"},
        {"en_US": "Quality management system re-certified for the 2026 cycle.",
         "th_TH": "ระบบบริหารคุณภาพผ่านการรับรองรอบใหม่ประจำปี 2026"},
        {"en_US": "<p>Our quality management system has successfully passed its "
                  "re-certification audit for the ISO 9001:2015 standard. The audit covered "
                  "project delivery, service operations and procurement across both the "
                  "Bangkok head office and the Lam Luk Ka engineering centre.</p>"
                  "<h3>What this means for our customers</h3>"
                  "<ul><li>Documented, traceable project and service processes.</li>"
                  "<li>Measured response and resolution times for maintenance contracts.</li>"
                  "<li>A continuous-improvement loop fed by customer feedback.</li></ul>"
                  "<p>The team is now preparing for ISO 14001 environmental certification.</p>",
         "th_TH": "<p>ระบบบริหารคุณภาพของบริษัทผ่านการตรวจประเมินเพื่อต่ออายุการรับรองมาตรฐาน "
                  "ISO 9001:2015 เรียบร้อยแล้ว โดยครอบคลุมงานส่งมอบโครงการ งานบริการ และงานจัดซื้อ "
                  "ทั้งที่สำนักงานใหญ่กรุงเทพฯ และศูนย์วิศวกรรมลำลูกกา</p>"
                  "<h3>สิ่งที่ลูกค้าได้รับ</h3>"
                  "<ul><li>กระบวนการส่งมอบโครงการและงานบริการที่ตรวจสอบย้อนกลับได้</li>"
                  "<li>เวลาตอบสนองและแก้ไขที่วัดผลได้สำหรับสัญญาบริการ</li>"
                  "<li>วงจรพัฒนาต่อเนื่องที่ขับเคลื่อนด้วยเสียงจากลูกค้า</li></ul>"
                  "<p>ขณะนี้ทีมงานกำลังเตรียมความพร้อมสำหรับการรับรอง ISO 14001 ด้านสิ่งแวดล้อม</p>"}),
    (
        "blog_tag_news",
        "2026-06-05 09:00:00",
        {"en_US": "New EcoStruxure™ control room commissioned at a fuel terminal",
         "th_TH": "ส่งมอบห้องควบคุม EcoStruxure™ แห่งใหม่ให้คลังน้ำมัน"},
        {"en_US": "Integrated tank gauging, loading control and SCADA on a single platform.",
         "th_TH": "รวมระบบวัดระดับถัง ควบคุมการโหลด และ SCADA ไว้บนแพลตฟอร์มเดียว"},
        {"en_US": "<p>A new control room has been commissioned for a fuel terminal in the "
                  "eastern seaboard. The project integrates tank gauging, overfill prevention, "
                  "loading-arm control and a unified SCADA layer.</p>"
                  "<h3>Project highlights</h3>"
                  "<ul><li>Redundant radar gauging with servo back-up.</li>"
                  "<li>Fail-safe overfill prevention loop certified for the site.</li>"
                  "<li>Single operator view for tank, loading and alarm management.</li></ul>"
                  "<p>Commissioning was completed ahead of schedule and the site has since "
                  "run through a full month of steady-state operation.</p>",
         "th_TH": "<p>บริษัทได้ส่งมอบห้องควบคุมแห่งใหม่ให้คลังน้ำมันในพื้นที่ชายฝั่งตะวันออก "
                  "โดยผสานระบบวัดระดับถัง ระบบป้องกันน้ำมันล้น ระบบควบคุมแขนโหลด "
                  "และชั้น SCADA เข้าไว้ด้วยกัน</p>"
                  "<h3>จุดเด่นของโครงการ</h3>"
                  "<ul><li>ระบบวัดระดับด้วยเรดาร์พร้อมเซอร์โวสำรองแบบ redundant</li>"
                  "<li>วงจรป้องกันน้ำมันล้นแบบ fail-safe ที่ผ่านการรับรองของพื้นที่</li>"
                  "<li>มุมมองเดียวสำหรับผู้ปฏิบัติการ ทั้งถัง การโหลด และการจัดการสัญญาณเตือน</li></ul>"
                  "<p>การทดสอบส่งมอบเสร็จก่อนกำหนด และพื้นที่ได้เดินระบบเต็มรูปแบบมาหนึ่งเดือนแล้ว</p>"}),
    (
        "blog_tag_articles",
        "2026-07-22 09:00:00",
        {"en_US": "Why a modern SCADA layer matters for your plant",
         "th_TH": "ทำไมชั้น SCADA ที่ทันสมัยจึงสำคัญต่อโรงงานของคุณ"},
        {"en_US": "Five practical signs that your control layer is due for an upgrade.",
         "th_TH": "5 สัญญาณที่บอกว่าถึงเวลายกระดับระบบควบคุมของคุณ"},
        {"en_US": "<p>Most plants do not fail because their instruments are wrong — they fail "
                  "because the data from those instruments never reaches the person who needs "
                  "to act on it. A modern SCADA layer closes that gap.</p>"
                  "<h3>Five signs it is time to upgrade</h3>"
                  "<ol><li>Operators still keep paper logs next to the screen.</li>"
                  "<li>Alarms are acknowledged without being read.</li>"
                  "<li>Reports are assembled by hand in spreadsheets.</li>"
                  "<li>Historical data is lost after a few days.</li>"
                  "<li>Every vendor brings their own separate HMI.</li></ol>"
                  "<p>Our engineering team can assess your existing layer and propose a "
                  "step-by-step migration that keeps production running.</p>",
         "th_TH": "<p>โรงงานส่วนใหญ่ไม่ได้ล้มเพราะเครื่องมือวัดผิด แต่ล้มเพราะข้อมูลจากเครื่องมือวัด "
                  "ไปไม่ถึงมือคนที่ต้องตัดสินใจ ชั้น SCADA ที่ทันสมัยคือคำตอบของช่องว่างตรงนั้น</p>"
                  "<h3>5 สัญญาณที่บอกว่าถึงเวลายกระดับ</h3>"
                  "<ol><li>ผู้ปฏิบัติการยังจดบันทึกด้วยกระดาษข้างหน้าจอ</li>"
                  "<li>กดรับสัญญาณเตือนโดยไม่ได้อ่าน</li>"
                  "<li>รายงานยังต้องทำมือในสเปรดชีต</li>"
                  "<li>ข้อมูลย้อนหลังหายไปภายในไม่กี่วัน</li>"
                  "<li>แต่ละผู้ผลิตนำระบบ HMI แยกของตัวเองเข้ามา</li></ol>"
                  "<p>ทีมวิศวกรของเราพร้อมประเมินระบบเดิมของคุณและเสนอแนวทางย้ายระบบแบบเป็นขั้นตอน "
                  "โดยไม่กระทบการผลิต</p>"}),
    (
        "blog_tag_events",
        "2026-09-12 18:00:00",
        {"en_US": "AUTO TOGETHER 2025 — Customer Appreciation Night",
         "th_TH": "AUTO TOGETHER 2025 — งานขอบคุณลูกค้า"},
        {"en_US": "An evening with our customers, partners and engineering teams.",
         "th_TH": "ค่ำคืนแห่งความขอบคุณสำหรับลูกค้า พันธมิตร และทีมวิศวกรของเรา"},
        {"en_US": "<p>Thank you to the customers, partners and colleagues who joined "
                  "<strong>AUTO TOGETHER 2025</strong>. The evening was a chance to look back "
                  "on the projects delivered during the year and to preview what is coming "
                  "next in industrial, building and terminal automation.</p>"
                  "<p>We also recognised the service engineers with the fastest response "
                  "times of the year — a small thank-you for the work that happens out of "
                  "sight, on site, at any hour.</p>",
         "th_TH": "<p>ขอขอบคุณลูกค้า พันธมิตร และเพื่อนร่วมงานทุกท่านที่มาร่วมงาน "
                  "<strong>AUTO TOGETHER 2025</strong> ในค่ำคืนนี้ เราได้ย้อนดูโครงการที่ส่งมอบ "
                  "ตลอดทั้งปี และแนะนำสิ่งที่กำลังจะมาถึงในงานระบบอัตโนมัติอุตสาหกรรม อาคาร "
                  "และคลังน้ำมัน</p>"
                  "<p>ภายในงาน เราได้มอบรางวัลให้วิศวกรบริการที่มีเวลาตอบสนองเร็วที่สุดแห่งปี "
                  "เพื่อขอบคุณงานที่ทำอยู่หน้างานตลอดเวลาโดยที่ลูกค้ามองไม่เห็น</p>"}),
    (
        "blog_tag_events",
        "2026-10-10 09:00:00",
        {"en_US": "Auto Virtual Run 2026 — registration is open",
         "th_TH": "Auto Virtual Run 2026 — เปิดรับสมัครแล้ว"},
        {"en_US": "Run anywhere, any time, and help us support a good cause.",
         "th_TH": "วิ่งที่ไหน เมื่อไหร่ก็ได้ ร่วมสนับสนุนกิจกรรมเพื่อสังคมไปด้วยกัน"},
        {"en_US": "<p><strong>Auto Virtual Run 2026</strong> is our annual virtual running "
                  "challenge for employees, customers and partners. There is no start line to "
                  "travel to: pick your own route, log your distance and join the leaderboard.</p>"
                  "<h3>How it works</h3>"
                  "<ul><li>Register with your e-mail address.</li>"
                  "<li>Run or walk any distance between the event dates.</li>"
                  "<li>Submit your result to join the company leaderboard.</li></ul>"
                  "<p>All entry fees go to the company's community fund.</p>",
         "th_TH": "<p><strong>Auto Virtual Run 2026</strong> คือกิจกรรมวิ่งเสมือนประจำปีของเรา "
                  "เปิดให้พนักงาน ลูกค้า และพันธมิตรเข้าร่วม ไม่ต้องเดินทางไปจุดสตาร์ท "
                  "เลือกเส้นทางเองได้ บันทึกระยะทาง และขึ้นกระดานผู้นำร่วมกัน</p>"
                  "<h3>วิธีเข้าร่วม</h3>"
                  "<ul><li>สมัครด้วยอีเมลของคุณ</li>"
                  "<li>วิ่งหรือเดินระยะทางใดก็ได้ภายในช่วงเวลากิจกรรม</li>"
                  "<li>ส่งผลการวิ่งเพื่อขึ้นกระดานผู้นำของบริษัท</li></ul>"
                  "<p>ค่าสมัครทั้งหมดจะนำเข้ากองทุนเพื่อสังคมของบริษัท</p>"}),
]


def _od19_write_translations(record, values):
    """Write a ``{field: {lang: value}}`` mapping on any record.

    Odoo stores translations in two different layouts, and the mapping has to
    be shaped accordingly:

    * ``translate=True`` (``Char``/``Text``) keeps one entry per language inside
      the jsonb column, so ``{lang: value}`` can be handed over unchanged.
    * a callable translator (``html_translate``, which ``Html(translate=True)``
      resolves to) keeps a single source document and expects a *term based*
      mapping ``{lang: {source_term: translated_term}}``.  Passing a plain
      string there raises ``TypeError: 'str' object is not a mapping``.

    Using ``with_context(lang=...).write()`` instead is not an option either:
    for html translators it leaves the value of every language pointing at the
    same document.
    """
    active_langs = set(record.env["res.lang"].sudo().search([]).mapped("code"))
    for field_name, per_lang in values.items():
        translations = {
            lang: value for lang, value in per_lang.items() if lang in active_langs
        }
        if not translations:
            continue

        field = record._fields[field_name]
        if field.translate is True:
            record.update_field_translations(field_name, translations)
            continue
        if not callable(field.translate):
            continue

        # --- callable translator (html_translate) -------------------------
        # The source document is written first so the term dictionary can be
        # computed against the value that is actually stored.
        source_lang = "en_US"
        source_value = translations.get(source_lang)
        if source_value:
            record.with_context(lang=source_lang).write({field_name: source_value})
        other_langs = {
            lang: value for lang, value in translations.items() if lang != source_lang
        }
        if not other_langs:
            continue

        source_value = record.with_context(lang=source_lang)[field_name]
        if not source_value:
            _logger.warning(
                "No %s source value on %s(%s); translations skipped.",
                field_name, record._name, record.id,
            )
            continue

        source_terms = field.get_trans_terms(source_value)
        for lang, value in other_langs.items():
            if len(field.get_trans_terms(value)) != len(source_terms):
                _logger.warning(
                    "Term count mismatch for %s.%s (%s): %d source vs %d %s; "
                    "the translation falls back to the source text.",
                    record._name, field_name, record.id,
                    len(source_terms), len(field.get_trans_terms(value)), lang,
                )

        term_map = {}
        for source_term, per_term in field.get_translation_dictionary(
                source_value, other_langs).items():
            for lang, value in per_term.items():
                term_map.setdefault(lang, {})[source_term] = value
        if term_map:
            record.update_field_translations(field_name, term_map)


class BlogBlog(models.Model):
    _inherit = "blog.blog"

    @api.model
    def _od19_ensure_xmlid(self, name, record):
        data = self.env["ir.model.data"].sudo().search([
            ("module", "=", "od19_website"),
            ("name", "=", name),
            ("model", "=", record._name),
        ], limit=1)
        if data and data.res_id == record.id:
            return
        if data:
            data.res_id = record.id
        else:
            self.env["ir.model.data"].sudo().create({
                "module": "od19_website",
                "name": name,
                "model": record._name,
                "res_id": record.id,
                "noupdate": True,
            })

    # ------------------------------------------------------------------
    # main entry point (post_init_hook + <function> in data/blog_data.xml)
    # ------------------------------------------------------------------
    @api.model
    def od19_setup_blog(self):
        """Create/refresh the "News & Events" hub: blog, tags and sample posts."""
        blog = self.sudo().search([], order="sequence, id", limit=1)
        if not blog:
            blog = self.sudo().create({"name": BLOG_NAME["en_US"]})

        _od19_write_translations(blog, {
            "name": BLOG_NAME,
            "subtitle": BLOG_SUBTITLE,
            "content": BLOG_INTRO,
        })

        # --- Branded cover --------------------------------------------------
        # A database seeded from the Odoo sample data carries a stock demo
        # cover.  Swap it for the Auto-Info hero so the hub matches the rest of
        # the website; a cover the customer picked in the editor is left alone.
        properties = json_safe.loads(blog.cover_properties or "{}")
        background = properties.get("background-image", "none")
        if background in ("", "none") or "/website_blog/static/" in background:
            properties.update(BLOG_COVER)
            blog.sudo().write({"cover_properties": json_safe.dumps(properties)})

        # --- Tag category + tags -------------------------------------------
        category = self.env["blog.tag.category"].sudo().search(
            [("name", "=", TAG_CATEGORY_NAME["en_US"])], limit=1)
        if not category:
            category = self.env["blog.tag.category"].sudo().create(
                {"name": TAG_CATEGORY_NAME["en_US"]})
        _od19_write_translations(category, {"name": TAG_CATEGORY_NAME})

        tags = {}
        for xml_name, color, names in TAGS:
            tag = self.env.ref("od19_website.%s" % xml_name, raise_if_not_found=False)
            if not tag:
                tag = self.env["blog.tag"].sudo().search([("name", "=", names["en_US"])], limit=1)
            if not tag:
                tag = self.env["blog.tag"].sudo().create({
                    "name": names["en_US"],
                    "category_id": category.id,
                    "color": color,
                })
            tag.sudo().write({"category_id": category.id, "color": color})
            _od19_write_translations(tag, {"name": names})
            self._od19_ensure_xmlid(xml_name, tag)
            tags[xml_name] = tag

        # --- Sample posts ---------------------------------------------------
        # New posts are only created while the blog is still empty, so a blog
        # that the customer already filled in is never polluted.  Posts that
        # match one of the seeds are refreshed on every upgrade, which also
        # repairs the translations of an existing database.
        BlogPost = self.env["blog.post"].sudo()
        empty_blog = not blog.blog_post_ids
        # Index the existing posts by every language they already hold: a
        # database seeded before the translations were fixed carries the Thai
        # title under ``en_US``, and it still has to be recognised as a seed so
        # that this run can repair it.
        # Languages that are not installed in the current database raise
        # ``UserError: Invalid language code`` when used in ``with_context``;
        # skip them defensively instead of pre-computing the active set, which
        # can disagree with the environment's own language cache.
        existing = {}
        for post in blog.blog_post_ids:
            for lang in ("en_US", "th_TH"):
                try:
                    name = post.with_context(lang=lang).name
                except UserError:
                    continue
                if name:
                    existing[name] = post
        seeded = 0
        for xml_name, post_date, title, subtitle, content in _POSTS:
            post = existing.get(title["en_US"]) or existing.get(title.get("th_TH"))
            if not post:
                if not empty_blog:
                    continue
                post = BlogPost.create({
                    "blog_id": blog.id,
                    "name": title["en_US"],
                    "subtitle": subtitle["en_US"],
                    "content": content["en_US"],
                    "post_date": post_date,
                    "published_date": post_date,
                    "is_published": True,
                    "tag_ids": [(6, 0, [tags[xml_name].id])],
                })
                seeded += 1
            _od19_write_translations(post, {
                "name": title,
                "subtitle": subtitle,
                "content": content,
            })
        if seeded:
            _logger.info("Seeded %d sample blog post(s) for '%s'.", seeded, blog.name)

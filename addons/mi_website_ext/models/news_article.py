import logging
import feedparser
from dateutil import parser as date_parser
from datetime import timedelta
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class NewsArticle(models.Model):
    _name = "news.article"
    _description = "Artículo de Noticias Externas"
    _order = "published_date desc"

    title = fields.Char(required=True)
    summary = fields.Text()
    link = fields.Char(required=True)
    source = fields.Char()
    published_date = fields.Datetime()
    image_url = fields.Char()

    @api.model
    def load_external_news(self):
        _logger.warning("🚀 Iniciando carga de noticias externas...")

        today = fields.Date.today()
        existing_today = self.search_count([
            ("published_date", ">=", today),
            ("published_date", "<", today + timedelta(days=1))
        ])

        if existing_today > 0:
            _logger.warning("📌 Ya hay noticias cargadas hoy (%s). Se omite actualización.", today)
            return

        sources = [
            ("https://www.muycomputer.com/feed/", "MuyComputer"),
            ("https://diariodesign.com/feed/", "Diariodesign"),
            ("https://lamenteesmaravillosa.com/feed/", "La Mente es Maravillosa"),
            ("https://ielektro.es/feed/", "IElektro"),
            ("https://www.adslzone.net/feed/", "ADSLZone"),
        ]

        self.search([]).unlink() 
        MAX_ENTRIES_PER_FEED = 1
        MAX_TOTAL_ARTICLES = 5 
        articles = []

        existing_titles = set(self.search([]).mapped("title"))
        existing_links = set(self.search([]).mapped("link"))

        for url, source in sources:
            try:
                feed = feedparser.parse(url)
                if feed.bozo:
                    _logger.warning(f"❌ Error al procesar el RSS de {source}: {feed.bozo_exception}")
                    continue

                for entry in feed.entries[:MAX_ENTRIES_PER_FEED]:
                    if len(articles) >= MAX_TOTAL_ARTICLES:
                        break

                    title = entry.get("title", "Sin título")
                    summary = entry.get("summary", "")
                    link = entry.get("link", "")

                    if title in existing_titles or link in existing_links:
                        _logger.info("⏩ Noticia duplicada ignorada: %s", title)
                        continue

                    raw_date = entry.get("published", "")
                    try:
                        pub_date = date_parser.parse(raw_date) if raw_date else fields.Datetime.now()
                        if pub_date.tzinfo:
                            pub_date = pub_date.replace(tzinfo=None)
                    except Exception as e:
                        _logger.warning("⚠️ No se pudo parsear la fecha para %s: %s", title, e)
                        pub_date = fields.Datetime.now()

                    articles.append({
                        "title": title,
                        "summary": summary,
                        "link": link,
                        "source": source,
                        "published_date": pub_date,
                        "image_url": "",
                    })

                    existing_titles.add(title)
                    existing_links.add(link)

                if len(articles) >= MAX_TOTAL_ARTICLES:
                    break

            except Exception as e:
                _logger.error(f"❌ Error al procesar fuente {source}: {e}")

        _logger.warning("📊 Total de noticias encontradas: %d", len(articles))
        for a in articles:
            _logger.warning("📰 %s — %s", a["title"], a["link"])

        if articles:
            self.create(articles)
            _logger.warning("✅ Noticias externas guardadas correctamente.")
        else:
            _logger.warning("⚠️ No se guardaron noticias (lista vacía).")


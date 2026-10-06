# Part of Odoo. See LICENSE file for full copyright and licensing details.

import os
import time

import xapian

from odoo.tools import config

LOCK_RETRIES = 10
LOCK_RETRY_DELAY = 0.1


class Opian:
    def __init__(self, dbname, index):
        self.dbpath = os.path.join(config.filestore(dbname), "xapian", index)

    def exists(self):
        try:
            xapian.Database(self.dbpath).close()
        except xapian.DatabaseOpeningError:
            return False
        return True

    def _open_writable(self):
        # Xapian allows a single writer per index, across all processes: wait for the lock
        os.makedirs(self.dbpath, exist_ok=True)
        for attempt in range(LOCK_RETRIES):
            try:
                return xapian.WritableDatabase(self.dbpath, xapian.DB_CREATE_OR_OPEN)
            except xapian.DatabaseLockError:
                if attempt == LOCK_RETRIES - 1:
                    raise
                time.sleep(LOCK_RETRY_DELAY)

    def index(self, values):
        """Index ``values``, a dict ``{record_id: (text, scope)}``. A ``None`` value removes the record.
        The optional ``scope`` string allows to restrict the queries to the records having it.
        """
        # Xapian objects are not thread-safe: one term generator per call
        termgenerator = xapian.TermGenerator()
        termgenerator.set_stemmer(xapian.Stem("en"))
        db = self._open_writable()
        try:
            for record_id, value in values.items():
                id_term = f"Q{record_id}"
                if value is None:
                    db.delete_document(id_term)
                    continue
                text, scope = value
                doc = xapian.Document()
                termgenerator.set_document(doc)
                termgenerator.index_text(text)
                doc.set_data(str(record_id))
                doc.add_boolean_term(id_term)
                if scope:
                    doc.add_boolean_term(f"XS{scope}")
                db.replace_document(id_term, doc)
            db.commit()
        finally:
            db.close()

    def query(self, text, scope=None):
        """Return the ids of all the records whose indexed text matches ``text``, among the records
        indexed with ``scope`` if given.
        """
        try:
            db = xapian.Database(self.dbpath)
        except xapian.DatabaseOpeningError:
            return []  # nothing indexed yet
        try:
            parser = xapian.QueryParser()
            parser.set_stemmer(xapian.Stem("en"))
            parser.set_stemming_strategy(xapian.QueryParser.STEM_SOME)
            parser.set_database(db)
            parser.set_default_op(xapian.Query.OP_AND)
            try:
                # FLAG_PARTIAL: the last word also matches as a prefix, for search-as-you-type
                query = parser.parse_query(text, xapian.QueryParser.FLAG_DEFAULT | xapian.QueryParser.FLAG_PARTIAL)
            except xapian.QueryParserError:
                return []
            if scope:
                query = xapian.Query(xapian.Query.OP_FILTER, query, xapian.Query(f"XS{scope}"))
            enquire = xapian.Enquire(db)
            enquire.set_query(query)
            # results are filtered and ordered by the SQL query, relevance is not needed
            enquire.set_weighting_scheme(xapian.BoolWeight())
            return [int(match.document.get_data()) for match in enquire.get_mset(0, db.get_doccount())]
        finally:
            db.close()

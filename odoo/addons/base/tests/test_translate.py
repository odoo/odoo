# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tools import pycompat
from odoo.tools import mute_logger
from odoo.tools.translate import quote, unquote, xml_translate, html_translate
from odoo.tests.common import TransactionCase, BaseCase
from psycopg2 import IntegrityError


class TranslationToolsTestCase(BaseCase):
    def assertItemsEqual(self, a, b, msg=None):
        self.assertEqual(sorted(a), sorted(b), msg)

    def test_quote_unquote(self):

        def test_string(str):
            quoted = quote(str)
            #print "\n1:", repr(str)
            #print "2:", repr(quoted)
            unquoted = unquote("".join(quoted.split('"\n"')))
            #print "3:", repr(unquoted)
            self.assertEquals(str, unquoted)

        test_string("""test \nall kinds\n \n o\r
         \\\\ nope\n\n"
         """)

        # The ones with 1+ backslashes directly followed by
        # a newline or literal N can fail... we would need a
        # state-machine parser to handle these, but this would
        # be much slower so it's better to avoid them at the moment
        self.assertRaises(AssertionError, quote, """test \nall kinds\n\no\r
         \\\\nope\n\n"
         """)

    def test_translate_xml_base(self):
        """ Test xml_translate() without formatting elements. """
        terms = []
        source = """<form string="Form stuff">
                        <h1>Blah blah blah</h1>
                        Put some more text here
                        <field name="foo"/>
                    </form>"""
        result = xml_translate(terms.append, source)
        self.assertEquals(result, source)
        self.assertItemsEqual(terms,
            ['Form stuff', 'Blah blah blah', 'Put some more text here'])

    def test_translate_xml_text(self):
        """ Test xml_translate() on plain text. """
        terms = []
        source = "Blah blah blah"
        result = xml_translate(terms.append, source)
        self.assertEquals(result, source)
        self.assertItemsEqual(terms, [source])

    def test_translate_xml_unicode(self):
        """ Test xml_translate() on plain text with unicode characters. """
        terms = []
        source = u"Un heureux évènement"
        result = xml_translate(terms.append, source)
        self.assertEquals(result, source)
        self.assertItemsEqual(terms, [source])

    def test_translate_xml_text_entity(self):
        """ Test xml_translate() on plain text with HTML escaped entities. """
        terms = []
        source = "Blah&amp;nbsp;blah&amp;nbsp;blah"
        result = xml_translate(terms.append, source)
        self.assertEquals(result, source)
        self.assertItemsEqual(terms, [source])

    def test_translate_xml_inline1(self):
        """ Test xml_translate() with formatting elements. """
        terms = []
        source = """<form string="Form stuff">
                        <h1>Blah <i>blah</i> blah</h1>
                        Put some <b>more text</b> here
                        <field name="foo"/>
                    </form>"""
        result = xml_translate(terms.append, source)
        self.assertEquals(result, source)
        self.assertItemsEqual(terms,
            ['Form stuff', 'Blah <i>blah</i> blah', 'Put some <b>more text</b> here'])

    def test_translate_xml_inline2(self):
        """ Test xml_translate() with formatting elements embedding other elements. """
        terms = []
        source = """<form string="Form stuff">
                        <b><h1>Blah <i>blah</i> blah</h1></b>
                        Put <em>some <b>more text</b></em> here
                        <field name="foo"/>
                    </form>"""
        result = xml_translate(terms.append, source)
        self.assertEquals(result, source)
        self.assertItemsEqual(terms,
            ['Form stuff', 'Blah <i>blah</i> blah', 'Put <em>some <b>more text</b></em> here'])

    def test_translate_xml_inline3(self):
        """ Test xml_translate() with formatting elements without actual text. """
        terms = []
        source = """<form string="Form stuff">
                        <div>
                            <span class="before"/>
                            <h1>Blah blah blah</h1>
                            <span class="after">
                                <i class="hack"/>
                            </span>
                        </div>
                    </form>"""
        result = xml_translate(terms.append, source)
        self.assertEquals(result, source)
        self.assertItemsEqual(terms,
            ['Form stuff', 'Blah blah blah'])

    def test_translate_xml_inline4(self):
        """ Test xml_translate() with inline elements with translated attrs only. """
        terms = []
        source = """<form string="Form stuff">
                        <div>
                            <label for="stuff"/>
                            <span class="fa fa-globe" title="Title stuff"/>
                        </div>
                    </form>"""
        result = xml_translate(terms.append, source)
        self.assertEquals(result, source)
        self.assertItemsEqual(terms,
            ['Form stuff', '<span class="fa fa-globe" title="Title stuff"/>'])

    def test_translate_xml_inline5(self):
        """ Test xml_translate() with inline elements with empty translated attrs only. """
        terms = []
        source = """<form string="Form stuff">
                        <div>
                            <label for="stuff"/>
                            <span class="fa fa-globe" title=""/>
                        </div>
                    </form>"""
        result = xml_translate(terms.append, source)
        self.assertEquals(result, source)
        self.assertItemsEqual(terms, ['Form stuff'])

    def test_translate_xml_t(self):
        """ Test xml_translate() with t-* attributes. """
        terms = []
        source = """<t t-name="stuff">
                        stuff before
                        <span t-field="o.name"/>
                        stuff after
                    </t>"""
        result = xml_translate(terms.append, source)
        self.assertEquals(result, source)
        self.assertItemsEqual(terms,
            ['stuff before', 'stuff after'])

    def test_translate_xml_off(self):
        """ Test xml_translate() with attribute translate="off". """
        terms = []
        source = """<div>
                        stuff before
                        <div t-translation="off">Do not translate this</div>
                        stuff after
                    </div>"""
        result = xml_translate(terms.append, source)
        self.assertEquals(result, source)
        self.assertItemsEqual(terms,
            ['stuff before', 'stuff after'])

    def test_translate_xml_attribute(self):
        """ Test xml_translate() with <attribute> elements. """
        terms = []
        source = """<field name="foo" position="attributes">
                        <attribute name="string">Translate this</attribute>
                        <attribute name="option">Do not translate this</attribute>
                    </field>"""
        result = xml_translate(terms.append, source)
        self.assertEquals(result, source)
        self.assertItemsEqual(terms,
            ['Translate this'])

    def test_translate_xml_a(self):
        """ Test xml_translate() with <a> elements. """
        terms = []
        source = """<t t-name="stuff">
                        <ul class="nav navbar-nav">
                            <li class="nav-item">
                                <a class="nav-link oe_menu_leaf" href="/web#menu_id=42&amp;action=54">
                                    <span class="oe_menu_text">Blah</span>
                                </a>
                            </li>
                        </ul>
                    </t>"""
        result = xml_translate(terms.append, source)
        self.assertEquals(result, source)
        self.assertItemsEqual(terms,
            ['<span class="oe_menu_text">Blah</span>'])

    def test_translate_xml_with_namespace(self):
        """ Test xml_translate() on elements with namespaces. """
        terms = []
        # do not slit the long line below, otherwise the result will not match
        source = """<Invoice xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">
                        <cbc:UBLVersionID t-esc="version_id"/>
                        <t t-foreach="[1, 2, 3, 4]" t-as="value">
                            Oasis <cac:Test t-esc="value"/>
                        </t>
                    </Invoice>"""
        result = xml_translate(terms.append, source)
        self.assertEquals(result, source)
        self.assertItemsEqual(terms, ['Oasis'])
        result = xml_translate(lambda term: term, source)
        self.assertEquals(result, source)

    def test_translate_xml_invalid_translations(self):
        """ Test xml_translate() with invalid translations. """
        source = """<form string="Form stuff">
                        <h1>Blah <i>blah</i> blah</h1>
                        Put some <b>more text</b> here
                        <field name="foo"/>
                    </form>"""
        translations = {
            "Put some <b>more text</b> here": "Mettre <b>plus de texte</i> ici",
        }
        expect = """<form string="Form stuff">
                        <h1>Blah <i>blah</i> blah</h1>
                        Mettre &lt;b&gt;plus de texte&lt;/i&gt; ici
                        <field name="foo"/>
                    </form>"""
        result = xml_translate(translations.get, source)
        self.assertEquals(result, expect)

    def test_translate_html(self):
        """ Test html_translate(). """
        source = """<blockquote>A <h2>B</h2> C</blockquote>"""
        result = html_translate(lambda term: term, source)
        self.assertEquals(result, source)

    def test_translate_html_i(self):
        """ Test xml_translate() and html_translate() with <i> elements. """
        source = """<p>A <i class="fa-check"></i> B</p>"""
        result = xml_translate(lambda term: term, source)
        self.assertEquals(result, """<p>A <i class="fa-check"/> B</p>""")
        result = html_translate(lambda term: term, source)
        self.assertEquals(result, source)


class TestTranslation(TransactionCase):

    def setUp(self):
        super(TestTranslation, self).setUp()
        self.env['ir.translation'].load_module_terms(['base'], ['fr_FR'])
        self.customers = self.env['res.partner.category'].create({'name': 'Customers'})
        self.env['ir.translation'].create({
            'type': 'model',
            'name': 'res.partner.category,name',
            'module':'base',
            'lang': 'fr_FR',
            'res_id': self.customers.id,
            'value': 'Clients',
            'state': 'translated',
        })

    def test_101_create_translated_record(self):
        category = self.customers.with_context({})
        self.assertEqual(category.name, 'Customers', "Error in basic name_get")

        category_fr = category.with_context({'lang': 'fr_FR'})
        self.assertEqual(category_fr.name, 'Clients', "Translation not found")

    def test_102_duplicate_record(self):
        category = self.customers.with_context({'lang': 'fr_FR'}).copy()

        category_no = category.with_context({})
        self.assertEqual(category_no.name, 'Customers', "Duplication did not set untranslated value")

        category_fr = category.with_context({'lang': 'fr_FR'})
        self.assertEqual(category_fr.name, 'Clients', "Did not found translation for initial value")

    def test_103_duplicate_record_fr(self):
        category = self.customers.with_context({'lang': 'fr_FR'}).copy({'name': 'Clients (copie)'})

        category_no = category.with_context({})
        self.assertEqual(category_no.name, 'Clients (copie)', "Duplication should set untranslated value")

        category_fr = category.with_context({'lang': 'fr_FR'})
        self.assertEqual(category_fr.name, 'Clients (copie)', "Did not used default value for translated value")

    def test_104_orderby_translated_field(self):
        """ Test search ordered by a translated field. """
        # create a category with a French translation
        padawans = self.env['res.partner.category'].create({'name': 'Padawans'})
        padawans_fr = padawans.with_context(lang='fr_FR')
        padawans_fr.write({'name': 'Apprentis'})
        # search for categories, and sort them by (translated) name
        categories = padawans_fr.search([('id', 'in', [self.customers.id, padawans.id])], order='name')
        self.assertEqual(categories.ids, [padawans.id, self.customers.id],
            "Search ordered by translated name should return Padawans (Apprentis) before Customers (Clients)")

    def test_105_duplicated_translation(self):
        """ Test synchronizing translations with duplicated source """
        # create a category with a French translation
        padawans = self.env['res.partner.category'].create({'name': 'Padawan'})
        self.env['ir.translation'].create({
            'type': 'model',
            'name': 'res.partner.category,name',
            'module':'base',
            'lang': 'fr_FR',
            'res_id': padawans.id,
            'value': 'Apprenti',
            'state': 'translated',
        })
        # change name and insert a duplicate manually
        padawans.write({'name': 'Padawans'})
        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'):
            with self.env.cr.savepoint():
                self.env['ir.translation'].create({
                    'type': 'model',
                    'name': 'res.partner.category,name',
                    'module':'base',
                    'lang': 'fr_FR',
                    'res_id': padawans.id,
                    'value': 'Apprentis',
                    'state': 'translated',
                })
        self.env['ir.translation'].translate_fields('res.partner.category', padawans.id, 'name')
        translations = self.env['ir.translation'].search([
            ('res_id', '=', padawans.id), ('name', '=', 'res.partner.category,name')
        ])
        self.assertEqual(len(translations), 1, "Translations were not duplicated after `translate_fields` call")
        self.assertEqual(translations.value, "Apprenti", "The first translation must stay")


class TestXMLTranslation(TransactionCase):
    def setUp(self):
        super(TestXMLTranslation, self).setUp()
        self.env['ir.translation'].load_module_terms(['base'], ['fr_FR', 'nl_NL'])

    def create_view(self, archf, terms, **kwargs):
        view = self.env['ir.ui.view'].create({
            'name': 'test',
            'model': 'res.partner',
            'arch': archf % terms,
        })
        for lang, trans_terms in kwargs.items():
            for src, val in pycompat.izip(terms, trans_terms):
                self.env['ir.translation'].create({
                    'type': 'model_terms',
                    'name': 'ir.ui.view,arch_db',
                    'lang': lang,
                    'res_id': view.id,
                    'src': src,
                    'value': val,
                    'state': 'translated',
                })
        return view

    def test_copy(self):
        """ Create a simple view, fill in translations, and copy it. """
        archf = '<form string="%s"><div>%s</div><div>%s</div></form>'
        terms_en = ('Knife', 'Fork', 'Spoon')
        terms_fr = ('Couteau', 'Fourchette', 'Cuiller')
        view0 = self.create_view(archf, terms_en, fr_FR=terms_fr)

        env_en = self.env(context={})
        env_fr = self.env(context={'lang': 'fr_FR'})

        # check translated field
        self.assertEqual(view0.with_env(env_en).arch_db, archf % terms_en)
        self.assertEqual(view0.with_env(env_fr).arch_db, archf % terms_fr)

        # copy without lang
        view1 = view0.with_env(env_en).copy({})
        self.assertEqual(view1.with_env(env_en).arch_db, archf % terms_en)
        self.assertEqual(view1.with_env(env_fr).arch_db, archf % terms_fr)

        # copy with lang='fr_FR'
        view2 = view0.with_env(env_fr).copy({})
        self.assertEqual(view2.with_env(env_en).arch_db, archf % terms_en)
        self.assertEqual(view2.with_env(env_fr).arch_db, archf % terms_fr)

        # copy with lang='fr_FR' and translate=html_translate
        self.patch(type(self.env['ir.ui.view']).arch_db, 'translate', html_translate)
        view3 = view0.with_env(env_fr).copy({})
        self.assertEqual(view3.with_env(env_en).arch_db, archf % terms_en)
        self.assertEqual(view3.with_env(env_fr).arch_db, archf % terms_fr)

    def test_spaces(self):
        """ Create translations where value has surrounding spaces. """
        archf = '<form string="%s"><div>%s</div><div>%s</div></form>'
        terms_en = ('Knife', 'Fork', 'Spoon')
        terms_fr = (' Couteau', 'Fourchette ', ' Cuiller ')
        self.create_view(archf, terms_en, fr_FR=terms_fr)

    def test_sync(self):
        """ Check translations after minor change in source terms. """
        archf = '<form string="X">%s</form>'
        terms_en = ('Bread and cheeze',)
        terms_fr = ('Pain et fromage',)
        terms_nl = ('Brood and kaas',)
        view = self.create_view(archf, terms_en, fr_FR=terms_fr, nl_NL=terms_nl)

        env_en = self.env(context={})
        env_fr = self.env(context={'lang': 'fr_FR'})
        env_nl = self.env(context={'lang': 'nl_NL'})

        self.assertEqual(view.with_env(env_en).arch_db, archf % terms_en)
        self.assertEqual(view.with_env(env_fr).arch_db, archf % terms_fr)
        self.assertEqual(view.with_env(env_nl).arch_db, archf % terms_nl)

        # modify source term in view (fixed type in 'cheeze')
        terms_en = ('Bread and cheese',)
        view.write({'arch_db': archf % terms_en})

        # check whether translations have been synchronized
        self.assertEqual(view.with_env(env_en).arch_db, archf % terms_en)
        self.assertEqual(view.with_env(env_fr).arch_db, archf % terms_fr)
        self.assertEqual(view.with_env(env_nl).arch_db, archf % terms_nl)

    def test_sync_update(self):
        """ Check translations after minor change in source terms. """
        archf = '<form string="X"><div>%s</div><div>%s</div></form>'
        terms_src = ('Subtotal', 'Subtotal:')
        terms_en = ('Subtotal', 'Sub total:')
        view = self.create_view(archf, terms_src, en_US=terms_en)

        translations = self.env['ir.translation'].search([
            ('type', '=', 'model_terms'),
            ('name', '=', "ir.ui.view,arch_db"),
            ('res_id', '=', view.id),
        ])
        self.assertEqual(len(translations), 2)

        # modifying the arch should sync existing translations without errors
        view.write({
            "arch": archf % ('Subtotal', 'Subtotal:<br/>')
        })

        translations = self.env['ir.translation'].search([
            ('type', '=', 'model_terms'),
            ('name', '=', "ir.ui.view,arch_db"),
            ('res_id', '=', view.id),
        ])
        # 'Subtotal' being src==value, it will be discared
        # 'Subtotal:' will be discarded as it match 'Subtotal' instead of 'Subtotal:<br/>'
        self.assertEqual(len(translations), 0)

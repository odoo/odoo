from odoo.tests.common import TransactionCase


class TestIrTranslation(TransactionCase):
    def _assert_detected_lang(self, descr, terms, lg_code_expected, term_ratio_expected=1.):
        """Execute ir_translation._guess_language_of_terms on the provided terms and asserts that:

        - the detected language is lg_code_expected
        - the term_ratio is term_ratio_expected with precision of 2 digits
        :param str descr: test description that will be outputted when an assertion fails
        :param list(str) terms: list of terms for the language detection
        :param str lg_code_expected: expected language code to be detected
        :param float term_ratio_expected: expected term ratio of the detection
        """
        actual_lang_code, actual_term_ratio = self.env['ir.translation']._guess_language_of_terms(terms)
        self.assertEqual(actual_lang_code, lg_code_expected,
                         f'[{descr}] Expected {lg_code_expected} for terms {terms} but got {actual_lang_code}')
        self.assertAlmostEqual(
            term_ratio_expected, actual_term_ratio,
            msg=f'[{descr}] Ratio ({actual_term_ratio})!={term_ratio_expected} for terms {terms} ({lg_code_expected})',
            places=2)

    @staticmethod
    def _transform(terms, transformations):
        """Transform the terms with the provided transformations

        :param list(str) terms: terms to transform
        :param list(str) transformations: transformations to apply among upper, lower and spaces
        :return: transformed terms
        """
        if not transformations:
            return terms
        for transformation in transformations:
            if transformation == 'upper':
                terms = [term.upper() for term in terms]
            elif transformation == 'lower':
                terms = [term.lower() for term in terms]
            elif transformation == 'spaces':
                terms = [f'  {term.lower()}  ' for term in terms]
            else:
                raise NotImplementedError(f'Transformation {transformation} not implemented')
        return terms

    @staticmethod
    def _translate_and_transform(trans_by_lg_code, lang_code, terms, transformations=None):
        """Translate and transform terms

        :param dict trans_by_lg_code: translation mappings (lang_code -> src -> translated_term)
        :param str lang_code: target language of the translation
        :param list(str) terms: terms to translate (in en_US contained in trans_by_lg_code as src)
        :param transformations: transformation to apply (see _transform)
        """
        translated_terms = terms
        if lang_code in trans_by_lg_code:
            translations = trans_by_lg_code[lang_code]
            translated_terms = {translations.get(term, term) for term in terms}
        return TestIrTranslation._transform(translated_terms, transformations)

    def test_guess_language_of_terms(self):
        """Test the detection of the language based on terms present in the table ir.translation."""
        Cls = TestIrTranslation
        IrTranslation = self.env['ir.translation']
        ResLang = self.env['res.lang']
        trans_by_lg_code = {
            'fr_BE': {
                'Confirm': 'Confirmer',
                'Cancel': 'Annuler',
                'Ok': 'Ok',
                'email': 'e-mail',
            },
            'nl_BE': {
                'Confirm': 'Bevestigen',
                'Validate': 'Bevestigen',  # Twice "Bevestigen" to test that it is counted only once
                'Cancel': 'Annuleren',
                'Ok': 'Ok',
                'email': 'e-mail',
            }
        }
        # Activate tested language
        for lg_code in trans_by_lg_code:
            lang = ResLang.search([('code', '=', lg_code), ('active', '!=', True)])
            if lang:
                lang.action_unarchive()
        # Remove all model translation to avoid interference with the test
        self.env['ir.translation'].search([('type', '=', 'model')]).unlink()
        # Create specific translation for the test
        IrTranslation.create([
            {
                'name': 'ir.model.fields,field_description',
                'lang': lg_code,
                'src': src,
                'value': value,
                'type': 'model',
            }
            for lg_code, translations in trans_by_lg_code.items() for src, value in translations.items()
        ])

        for transformations in [None, ['lower'], ['upper'], ['upper', 'spaces']]:
            for lang_code in trans_by_lg_code:
                self._assert_detected_lang(
                    f'All terms in {lang_code} ({transformations})',
                    Cls._translate_and_transform(trans_by_lg_code, lang_code, ['Confirm', 'Cancel'],
                                                 transformations=transformations),
                    lang_code)
                self._assert_detected_lang(
                    f'2/3 in {lang_code} ({transformations})',
                    Cls._translate_and_transform(trans_by_lg_code, lang_code, ['Confirm', 'Cancel', 'NonExists'],
                                                 transformations=transformations),
                    lang_code, term_ratio_expected=0.67)
            self._assert_detected_lang(f'Mixed languages ({transformations})',
                                       Cls._transform(['Confirm', 'Confirmer', 'Bevestigen', 'Annuleren'],
                                                      transformations),
                                       'nl_BE', term_ratio_expected=0.5)
            self._assert_detected_lang(
                f'Shared terms between language with 1 word to decide between languages ({transformations})',
                Cls._transform(['Ok', 'e-mail', 'Bevestigen'], transformations),
                'nl_BE')
            self._assert_detected_lang(
                f'Mixed languages (base language, {transformations})',
                Cls._transform(['Confirm', 'Confirmer', 'Bevestigen', 'Cancel'], transformations),
                'en_US', term_ratio_expected=0.5)
            self._assert_detected_lang(
                f'Shared terms between language with one word to decide between languages (base lg, {transformations})',
                Cls._transform(['Ok', 'email'], transformations),
                'en_US')
        self.assertEqual(IrTranslation._guess_language_of_terms(['NonExists1', 'NonExists2'])[0], None)

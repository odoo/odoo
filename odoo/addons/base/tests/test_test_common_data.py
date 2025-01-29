from odoo.tests.common import TransactionCase, data_depends


RUN_ORDER = [
    'ExtendedCommonDataCommonCase',
    'CommonDataCommonCase',
    'DiamondInheritCommonDataTest',
    'DiamondInheritCommonDataTest2',
]

class CommonDataCommonCase(TransactionCase):
    test_sequence = -10
    _cls_history_names = []

    @classmethod
    def _get_run_order(cls):
        def _non_raise_index(name):
            try:
                return RUN_ORDER.index(name)
            except ValueError:
                return None
        idx = next(iter(k_idx for kls in cls.__mro__ if (k_idx := _non_raise_index(kls.__name__)) is not None))
        return RUN_ORDER[:idx + 1]

    @classmethod
    def _get_partner_name(cls):
        return 'Goofy'
    
    @data_depends('_get_partner_name')
    @classmethod
    def setUpCommonData(cls):
        cls._cls_history_names.append(cls.__name__)
        cls.partner = cls.env['res.partner'].create({'name': cls._get_partner_name()})


class CommonDataTest(CommonDataCommonCase):

    def test_partner_name(self):
        # Relies on all tests in this file being ran in order.
        self.assertEqual(
            self._cls_history_names,
            self._get_run_order(),
        )
        self.assertEqual(self.partner.name, self._get_partner_name())


class ExtendedCommonDataCommonCase(CommonDataCommonCase):

    @classmethod
    def _get_partner_name(cls):
        return 'Mickey'
    
    @classmethod
    def setUpCommonData(cls):
        cls.env = cls.env(context={'from_extended': True})

class DoublyExtendedCommonDataCommonCase(ExtendedCommonDataCommonCase):
    pass


class ExtendedCommonDataTest1(ExtendedCommonDataCommonCase):

    @classmethod
    def setUpCommonData(cls):
        # The following tests that `setUpCommonData` cache key for `ExtendedCommonDataCommonCase`
        # will still be ran with the common class and not this implementation class.
        pass

    def test_partner_name(self):
        # Relies on all tests in this file being ran in order.
        self.assertEqual(
            self._cls_history_names,
            self._get_run_order(),
        )
        self.assertEqual(self.partner.name, self._get_partner_name())
        self.assertTrue(self.env.context['from_extended'])


class ExtendedCommonDataTest2(ExtendedCommonDataCommonCase):

    def test_partner_name(self):
        # Relies on all tests in this file being ran in order.
        self.assertEqual(
            self._cls_history_names,
            self._get_run_order(),
        )
        self.assertEqual(self.partner.name, self._get_partner_name())
        self.assertTrue(self.env.context['from_extended'])

class DoublyExtendedCommonDataTest(DoublyExtendedCommonDataCommonCase):
    test_sequence = -15

    @classmethod
    def setUpCommonData(cls):
        pass

    def test_partner_name(self):
        # Relies on all tests in this file being ran in order.
        self.assertEqual(
            self._cls_history_names,
            self._get_run_order(),
        )
        self.assertEqual(self.partner.name, self._get_partner_name())
        self.assertTrue(self.env.context['from_extended'])

class OtherExtendedCommonDataCommonCase(CommonDataCommonCase):

    @classmethod
    def _get_partner_name(cls):
        return 'Minnie'


class DiamondInheritCommonDataTest(OtherExtendedCommonDataCommonCase, ExtendedCommonDataCommonCase):

    def test_partner_name(self):
        # Relies on all tests in this file being ran in order.
        self.assertEqual(
            self._cls_history_names,
            self._get_run_order(),
        )
        self.assertEqual(self.partner.name, self._get_partner_name())

# Calling twice as it has the same exact dependencies as DiamonInheritCommonDataTest, however they can't share data
# as both require everything to be installed on themselves.
class DiamondInheritCommonDataTest2(OtherExtendedCommonDataCommonCase, ExtendedCommonDataCommonCase):

    def test_partner_name(self):
        # Relies on all tests in this file being ran in order.
        self.assertEqual(
            self._cls_history_names,
            self._get_run_order(),
        )
        self.assertEqual(self.partner.name, self._get_partner_name())


# Testing for env's lazy_property cache invalidation between tests
class CommonDataCommonCase2(TransactionCase):
    test_sequence = -10

    @classmethod
    def setUpCommonData(cls):
        cls.partner = cls.env['res.partner'].create({'name': 'Test Partner'})
        cls.partner.env.companies


class DataTest1(CommonDataCommonCase2):

    def test_env_companies(self):
        self.env.user.company_ids += self.env['res.company'].create({'name': 'Test Company'})
        self.assertEqual(
            self.partner.env.companies,
            self.env.user.company_ids,
        )

class DataTest2(CommonDataCommonCase2):

    def test_env_companies(self):
        self.assertEqual(
            self.partner.env.companies,
            self.env.user.company_ids,
        )

# -*- coding: utf-8 -*-
"""
Unit-tests for pytils.typo
"""

import unittest
import os
from pytils import typo

def cb_testrule(x):
    return x

class HelpersTestCase(unittest.TestCase):
    """
    Test case for pytils.typo helpers
    """
    def testGetRuleByName(self):
        """
        unit-test for pytils.typo._get_rule_by_name
        """
        self.assert_(
            callable(
                typo._get_rule_by_name('testrule')
        ))
        self.assertEquals(
            'rl_testrule',
            typo._get_rule_by_name('testrule').__name__
        )
    
    def testResolveRule(self):
        """
        unit-test for pytils.typo._resolve_rule
        """
        self.assert_(
            callable(
                typo._resolve_rule_name('testrule')[1]
        ))
        self.assert_(
            callable(
                typo._resolve_rule_name(cb_testrule)[1]
        ))
        self.assertEquals(
            'testrule',
            typo._resolve_rule_name('testrule')[0]
        )
        self.assertEquals(
            'cb_testrule',
            typo._resolve_rule_name(cb_testrule)[0]
        )

    def testResolveRuleWithForcedName(self):
        """
        unit-test for pytils.typo._resolve_rule with forced_name arg
        """
        self.assert_(
            callable(typo._resolve_rule_name('testrule', 'newrule')[1]
        ))
        self.assert_(
            callable(typo._resolve_rule_name(cb_testrule, 'newrule')[1]
        ))
        self.assertEquals(
            'newrule',
            typo._resolve_rule_name('testrule', 'newrule')[0]
        )
        self.assertEquals(
            'newrule',
            typo._resolve_rule_name(cb_testrule, 'newrule')[0]
        )

class TypographyApplierTestCase(unittest.TestCase):
    """
    Test case for typography rule applier pytils.typo.Typography
    """
    def testExpandEmptyArgs(self):
        self.assertEquals(
            {},
            typo.Typography().rules
        )
        self.assertEquals(
            [],
            typo.Typography().rules_names
        )
    
    def testExpandSimpleStrArgs(self):
        self.assertEquals(
            {'testrule': typo.rl_testrule},
            typo.Typography('testrule').rules
        )
        self.assertEquals(
            ['testrule'],
            typo.Typography('testrule').rules_names
        )
    
    def testExpandDictStrArgs(self):
        self.assertEquals(
            {
                'testrule': typo.rl_testrule,
                'newrule':  typo.rl_testrule
            },
            typo.Typography('testrule', {'newrule': 'testrule'}).rules
        )
        self.assertEquals(
            ['testrule', 'newrule'],
            typo.Typography('testrule', {'newrule': 'testrule'}).rules_names
        )

    def testExpandSimpleCallableArgs(self):
        self.assertEquals(
            {'cb_testrule': cb_testrule},
            typo.Typography(cb_testrule).rules
        )
        self.assertEquals(
            ['cb_testrule'],
            typo.Typography(cb_testrule).rules_names
        )
    
    def testExpandDictCallableArgs(self):
        self.assertEquals(
            {
                'cb_testrule': cb_testrule,
                'newrule': cb_testrule
            },
            typo.Typography(cb_testrule, {'newrule': cb_testrule}).rules
        )
        self.assertEquals(
            ['cb_testrule', 'newrule'],
            typo.Typography(cb_testrule, {'newrule': cb_testrule}).rules_names
        )

    def testExpandMixedArgs(self):
        self.assertEquals(
            {
                'cb_testrule': cb_testrule,
                'newrule': typo.rl_testrule
            },
            typo.Typography(cb_testrule, newrule='testrule').rules
        )
        self.assertEquals(
            ['cb_testrule', 'newrule'],
            typo.Typography(cb_testrule, newrule='testrule').rules_names
        )
        self.assertEquals(
            {
                'cb_testrule': cb_testrule,
                'testrule': typo.rl_testrule
            },
            typo.Typography(cb_testrule, 'testrule').rules
        )
        self.assertEquals(
            ['cb_testrule', 'testrule'],
            typo.Typography(cb_testrule, 'testrule').rules_names
        )

    def testRecommendedArgsStyle(self):
        lambdarule = lambda x: x
        self.assertEquals(
            {
                'cb_testrule': cb_testrule,
                'testrule': typo.rl_testrule,
                'newrule': lambdarule
            },
            typo.Typography([cb_testrule], ['testrule'], {'newrule': lambdarule}).rules
        )
        self.assertEquals(
            ['cb_testrule', 'testrule', 'newrule'],
            typo.Typography([cb_testrule], ['testrule'], {'newrule': lambdarule}).rules_names
        )

class RulesTestCase(unittest.TestCase):

    def checkRule(self, name, input_value, expected_result):
        """
        Check how rule is acted on input_value with expected_result
        """
        self.assertEquals(
            expected_result,
            typo._get_rule_by_name(name)(input_value)
        )
    
    def testCleanspaces(self):
        """
        Unit-test for cleanspaces rule
        """
        self.checkRule(
            'cleanspaces',
            u" Точка ,точка , запятая, вышла рожица  кривая . ",
            u"Точка, точка, запятая, вышла рожица кривая."
        )
        self.checkRule(
            'cleanspaces',
            u" Точка ,точка , %(n)sзапятая,%(n)s вышла рожица  кривая . " % {'n': os.linesep},
            u"Точка, точка,%(n)sзапятая,%(n)sвышла рожица кривая." % {'n': os.linesep}
        )
        self.checkRule(
            'cleanspaces',
            u"Газета ( ее принес мальчишка утром ) всё еще лежала на столе.",
            u"Газета (ее принес мальчишка утром) всё еще лежала на столе.",
        )
        self.checkRule(
            'cleanspaces',
            u"Газета, утром принесенная мальчишкой ( это был сосед, подзарабатывающий летом ) , всё еще лежала на столе.",
            u"Газета, утром принесенная мальчишкой (это был сосед, подзарабатывающий летом), всё еще лежала на столе.",
        )
        self.checkRule(
            'cleanspaces',
            u"Что это?!?!",
            u"Что это?!?!",
        )

    def testEllipsis(self):
        """
        Unit-test for ellipsis rule
        """
        self.checkRule(
            'ellipsis',
            u"Быть или не быть, вот в чем вопрос...%(n)s%(n)sШекспир" % {'n': os.linesep},
            u"Быть или не быть, вот в чем вопрос…%(n)s%(n)sШекспир" % {'n': os.linesep}
        )
        self.checkRule(
            'ellipsis',
            u"Мдя..... могло быть лучше",
            u"Мдя..... могло быть лучше"
        )
        self.checkRule(
            'ellipsis',
            u"...Дааааа",
            u"…Дааааа"
        )
        self.checkRule(
            'ellipsis',
            u"... Дааааа",
            u"…Дааааа"
        )
        
    
    def testInitials(self):
        """
        Unit-test for initials rule
        """
        self.checkRule(
            'initials',
            u'Председатель В.И.Иванов выступил на собрании',
            u'Председатель В.И.\u2009Иванов выступил на собрании',
        )
        self.checkRule(
            'initials',
            u'Председатель В.И. Иванов выступил на собрании',
            u'Председатель В.И.\u2009Иванов выступил на собрании',
        )
        self.checkRule(
            'initials',
            u'1. В.И.Иванов%(n)s2. С.П.Васечкин'% {'n': os.linesep},
            u'1. В.И.\u2009Иванов%(n)s2. С.П.\u2009Васечкин' % {'n': os.linesep}
        )
        self.checkRule(
            'initials',
            u'Комиссия в составе директора В.И.Иванова и главного бухгалтера С.П.Васечкина постановила',
            u'Комиссия в составе директора В.И.\u2009Иванова и главного бухгалтера С.П.\u2009Васечкина постановила'
        )

    def testDashes(self):
        """
        Unit-test for dashes rule
        """
        self.checkRule(
            'dashes',
            u'- Я пошел домой... - Может останешься? - Нет, ухожу.',
            u'\u2014 Я пошел домой... \u2014 Может останешься? \u2014 Нет, ухожу.'
        )
        self.checkRule(
            'dashes',
            u'-- Я пошел домой... -- Может останешься? -- Нет, ухожу.',
            u'\u2014 Я пошел домой... \u2014 Может останешься? \u2014 Нет, ухожу.'
        )
        self.checkRule(
            'dashes',
            u'-- Я\u202fпошел домой…\u202f-- Может останешься?\u202f-- Нет,\u202fухожу.',
            u'\u2014 Я\u202fпошел домой…\u202f\u2014 Может останешься?\u202f\u2014 Нет,\u202fухожу.'
        )
        self.checkRule(
            'dashes',
            u'Ползать по-пластунски',
            u'Ползать по-пластунски',
        )
        self.checkRule(
            'dashes',
            u'Диапазон: 9-15',
            u'Диапазон: 9\u201315',
        )

    def testWordglue(self):
        """
        Unit-test for wordglue rule
        """
        self.checkRule(
            'wordglue',
            u'Вроде бы он согласен',
            u'Вроде\u202fбы\u202fон\u202fсогласен',
        )
        self.checkRule(
            'wordglue',
            u'Он не поверил своим глазам',
            u'Он\u202fне\u202fповерил своим\u202fглазам',
        )
        self.checkRule(
            'wordglue',
            u'Это - великий и ужасный Гудвин',
            u'Это\u202f- великий и\u202fужасный\u202fГудвин',
        )
        self.checkRule(
            'wordglue',
            u'Это \u2014 великий и ужасный Гудвин',
            u'Это\u202f\u2014 великий и\u202fужасный\u202fГудвин',
        )
        self.checkRule(
            'wordglue',
            u'-- Я пошел домой… -- Может останешься? -- Нет, ухожу.',
            u'-- Я\u202fпошел домой…\u202f-- Может останешься?\u202f-- Нет,\u202fухожу.'
        )
        self.checkRule(
            'wordglue',
            u'увидел в газете (это была "Сермяжная правда" № 45) рубрику Weather Forecast',
            u'увидел в\u202fгазете (это\u202fбыла "Сермяжная правда" № 45) рубрику Weather\u202fForecast',
        )
        

    def testMarks(self):
        """
        Unit-test for marks rule
        """
        self.checkRule(
            'marks',
            u"Когда В. И. Пупкин увидел в газете рубрику Weather Forecast(r), он не поверил своим глазам \u2014 температуру обещали +-451F.",
            u"Когда В. И. Пупкин увидел в газете рубрику Weather Forecast®, он не поверил своим глазам \u2014 температуру обещали ±451\u202f°F."
        )
        self.checkRule(
            'marks',
            u"14 Foo",
            u"14 Foo"
        )
        self.checkRule(
            'marks',
            u"Coca-cola(tm)",
            u"Coca-cola™"
        )
        self.checkRule(
            'marks',
            u'(c) 2008 Юрий Юревич',
            u'©\u202f2008 Юрий Юревич'
        )
        self.checkRule(
            'marks',
            u"Microsoft (R) Windows (tm)",
            u"Microsoft® Windows™"
        )
        self.checkRule(
            'marks',
            u"Школа-гимназия No 3",
            u"Школа-гимназия №\u20093",
        )
        self.checkRule(
            'marks',
            u"Школа-гимназия No3",
            u"Школа-гимназия №\u20093",
        )
        self.checkRule(
            'marks',
            u"Школа-гимназия №3",
            u"Школа-гимназия №\u20093",
        )

    def testQuotes(self):
        """
        Unit-test for quotes rule
        """
        self.checkRule(
            'quotes',
            u"ООО \"МСК \"Аско-Забота\"",
            u"ООО «МСК «Аско-Забота»"
        )
        self.checkRule(
            'quotes',
            u"ООО\u202f\"МСК\u202f\"Аско-Забота\"",
            u"ООО\u202f«МСК\u202f«Аско-Забота»"
        )
        self.checkRule(
            'quotes',
            u"Двигатели 'Pratt&Whitney'",
            u"Двигатели “Pratt&Whitney”"
        )
        self.checkRule(
            'quotes',
            u"\"Вложенные \"кавычки\" - бич всех типографик\", не правда ли",
            u"«Вложенные «кавычки» - бич всех типографик», не правда ли",
        )
        self.checkRule(
            'quotes',
            u"Двигатели 'Pratt&Whitney' никогда не использовались на самолетах \"Аэрофлота\"",
            u"Двигатели “Pratt&Whitney” никогда не использовались на самолетах «Аэрофлота»"
        )

class TypographyTestCase(unittest.TestCase):
    """
    Tests for pytils.typo.typography
    """
    def checkTypo(self, input_value, expected_value):
        """
        Helper for checking typo.typography
        """
        self.assertEquals(expected_value, typo.typography(input_value))
    
    def testPupkin(self):
        """
        Unit-test on pupkin-text
        """
        self.checkTypo(
        u"""...Когда В. И. Пупкин увидел в газете ( это была "Сермяжная правда" № 45) рубрику Weather Forecast(r), он не поверил своим глазам - температуру обещали +-451F.""",
        u"""…Когда В.И.\u2009Пупкин увидел в\u202fгазете (это\u202fбыла «Сермяжная правда» №\u200945) рубрику Weather Forecast®, он\u202fне\u202fповерил своим глазам\u202f\u2014 температуру обещали ±451\u202f°F.""")

if __name__ == '__main__':
    unittest.main()


# -*- coding: utf-8 -*-
# -*- test-case-name: pytils.test.test_typo -*-
"""
Russian typography
"""
import re
import os

def _sub_patterns(patterns, text):
    """
    Apply re.sub to bunch of (pattern, repl)
    """
    for pattern, repl in patterns:
        text = re.sub(pattern, repl, text)
    return text

## ---------- rules -------------
# rules is a regular function,
# name convention is rl_RULENAME
def rl_testrule(x):
    """
    Rule for tests. Do nothing.
    """
    return x

def rl_cleanspaces(x):
    """
    Clean double spaces, trailing spaces, heading spaces,
    spaces before punctuations
    """
    patterns = (
        # arguments for re.sub: pattern and repl
        # удаляем пробел перед знаками препинания
        (r' +([\.,?!\)]+)', r'\1'),
        # добавляем пробел после знака препинания, если только за ним нет другого
        (r'([\.,?!\)]+)([^\.!,?\)]+)', r'\1 \2'),
        # убираем пробел после открывающей скобки
        (r'(\S+)\s*(\()\s*(\S+)', r'\1 (\3'),
    )
    # удаляем двойные, начальные и конечные пробелы
    return os.linesep.join(
        ' '.join(part for part in line.split(' ') if part)
        for line in _sub_patterns(patterns, x).split(os.linesep)
    )

def rl_ellipsis(x):
    """
    Replace three dots to ellipsis
    """

    patterns = (
        # если больше трех точек, то не заменяем на троеточие
        # чтобы не было глупых .....->…..
        (r'([^\.]|^)\.\.\.([^\.]|$)', u'\\1\u2026\\2'),
        # если троеточие в начале строки или возле кавычки --
        # это цитата, пробел между троеточием и первым
        # словом нужно убрать
        (re.compile(u'(^|\\"|\u201c|\xab)\\s*\u2026\\s*([А-Яа-яA-Za-z])', re.UNICODE), u'\\1\u2026\\2'),
        
    )
    return _sub_patterns(patterns, x)

def rl_initials(x):
    """
    Replace space between initials and surname by thin space
    """
    return re.sub(
        re.compile(u'([А-Я])\\.\\s*([А-Я])\\.\\s*([А-Я][а-я]+)', re.UNICODE),
        u'\\1.\\2.\u2009\\3',
        x
    )

def rl_dashes(x):
    """
    Replace dash to long/medium dashes
    """
    patterns = (
        # тире
        (re.compile(u'(^|(.\\s))\\-\\-?(([\\s\u202f].)|$)', re.MULTILINE|re.UNICODE), u'\\1\u2014\\3'),
        # диапазоны между цифрами - en dash
        (re.compile(u'(\\d[\\s\u2009]*)\\-([\\s\u2009]*\d)', re.MULTILINE|re.UNICODE), u'\\1\u2013\\2'),
        # TODO: а что с минусом?
    )
    return _sub_patterns(patterns, x)

def rl_wordglue(x):
    """
    Glue (set nonbreakable space) short words with word before/after
    """
    patterns = (
        # частицы склеиваем с предыдущим словом
        (re.compile(u'(\\s+)(же|ли|ль|бы|б|ж|ка)([\\.,!\\?:;]?\\s+)', re.UNICODE), u'\u202f\\2\\3'),
        # склеиваем короткие слова со следующим словом
        (re.compile(u'\\b([a-zA-ZА-Яа-я]{1,3})(\\s+)', re.UNICODE), u'\\1\u202f'),
        # склеиваем тире с предыдущим словом
        (re.compile(u'(\\s+)([\u2014\\-]+)(\\s+)', re.UNICODE), u'\u202f\\2\\3'),
        # склеиваем два последних слова в абзаце между собой
        # полагается, что абзацы будут передаваться отдельной строкой
        (re.compile(u'([^\\s]+)\\s+([^\\s]+)$', re.UNICODE), u'\\1\u202f\\2'),
    )
    return _sub_patterns(patterns, x)

def rl_marks(x):
    """
    Replace +-, (c), (tm), (r), (p), etc by its typographic eqivalents
    """
    # простые замены, можно без регулярок
    replacements = (
        (u'(r)', u'\u00ae'), # ®
        (u'(R)', u'\u00ae'), # ®
        (u'(p)', u'\u00a7'), # §
        (u'(P)', u'\u00a7'), # §
        (u'(tm)', u'\u2122'), # ™
        (u'(TM)', u'\u2122'), # ™
    )
    patterns = (
        # копирайт ставится до года: © 2008 Юрий Юревич
        (re.compile(u'\\([cCсС]\\)\\s*(\\d+)', re.UNICODE), u'\u00a9\u202f\\1'),
        (r'([^+])(\+\-|\-\+)', u'\\1\u00b1'), # ±
        # градусы с минусом
        (u'\\-(\\d+)[\\s]*([FCС][^\\w])', u'\u2212\\1\202f\u00b0\\2'), # −12 °C, −53 °F
        # градусы без минуса
        (u'(\\d+)[\\s]*([FCС][^\\w])', u'\\1\u202f\u00b0\\2'), # 12 °C, 53 °F
        # ® и ™ приклеиваются к предыдущему слову, без пробела
        (re.compile(u'([A-Za-zА-Яа-я\\!\\?])\\s*(\xae|\u2122)', re.UNICODE), u'\\1\\2'),
        # No5 -> № 5
        (re.compile(u'(\\s)(No|no|NO|\u2116)[\\s\u2009]*(\\d+)', re.UNICODE), u'\\1\u2116\u2009\\3'),
    )

    for what, to in replacements:
        x = x.replace(what, to)
    return _sub_patterns(patterns, x)

def rl_quotes(x):
    """
    Replace quotes by typographic quotes
    """
    
    patterns = (
        # открывающие кавычки ставятся обычно вплотную к слову слева
        # а закрывающие -- вплотную справа
        # открывающие русские кавычки-ёлочки
        (re.compile(r'((?:^|\s))(")((?u))', re.UNICODE), u'\\1\xab\\3'),
        # закрывающие русские кавычки-ёлочки
        (re.compile(r'(\S)(")((?u))', re.UNICODE), u'\\1\xbb\\3'),
        # открывающие кавычки-лапки, вместо одинарных кавычек
        (re.compile(r'((?:^|\s))(\')((?u))', re.UNICODE), u'\\1\u201c\\3'),
        # закрывающие кавычки-лапки
	(re.compile(r'(\S)(\')((?u))', re.UNICODE), u'\\1\u201d\\3'),
    )
    return _sub_patterns(patterns, x)
    

## -------- rules end ----------
STANDARD_RULES = ('cleanspaces', 'ellipsis', 'initials', 'marks', 'dashes', 'wordglue', 'quotes')

def _get_rule_by_name(name):

    rule = globals().get('rl_%s' % name)
    if rule is None:
        raise ValueError("Rule %s is not found" % name)
    if not callable(rule):
        raise ValueError("Rule with name %s is not callable" % name)
    return rule

def _resolve_rule_name(rule_or_name, forced_name=None):
    if isinstance(rule_or_name, str):
        # got name
        name = rule_or_name
        rule = _get_rule_by_name(name)
    elif callable(rule_or_name):
        # got rule
        name = rule_or_name.__name__
        if name.startswith('rl_'):
            # by rule name convention
            # rule is a function with name rl_RULENAME
            name = name[3:]
        rule = rule_or_name
    else:
        raise ValueError(
            "Cannot resolve %r: neither rule, nor name" %
            rule_or_name)
    if forced_name is not None:
        name = forced_name
    return name, rule

class Typography(object):
    """
    Russian typography rules applier
    """
    def __init__(self, *args, **kwargs):
        """
        Typography applier constructor:
        
        possible variations of constructing rules chain:
            rules by it's names:
                Typography('first_rule', 'second_rule')
            rules callables as is:
                Typography(cb_first_rule, cb_second_rule)
            mixed:
                Typography('first_rule', cb_second_rule)
            as list:
                Typography(['first_rule', cb_second_rule])
            as keyword args:
                Typography(rule_name='first_rule',
                           another_rule=cb_second_rule)
            as dict (order of rule execution is not the same):
                Typography({'rule name': 'first_rule',
                            'another_rule': cb_second_rule})
        
        For standard rules it is recommended to use list of rules
        names.
            Typography(['first_rule', 'second_rule'])
        
        For custom rules which are named functions,
        it is recommended to use list of callables:
            Typography([cb_first_rule, cb_second_rule])
        
        For custom rules which are lambda-functions,
        it is recommended to use dict:
            Typography({'rule_name': lambda x: x})
            
        I.e. the recommended usage is:
            Typography(['standard_rule_1', 'standard_rule_2'],
                       [cb_custom_rule1, cb_custom_rule_2],
                       {'custom_lambda_rule': lambda x: x})
        """
        self.rules = {}
        self.rules_names = []
        # first of all, expand args-lists and args-dicts
        expanded_args = []
        expanded_kwargs = {}
        for arg in args:
            if isinstance(arg, (tuple, list)):
                expanded_args += list(arg)
            elif isinstance(arg, dict):
                expanded_kwargs.update(arg)
            elif isinstance(arg, str) or callable(arg):
                expanded_args.append(arg)
            else:
                raise TypeError(
                    "Cannot expand arg %r, must be tuple, list,"\
                    " dict, str or callable, not" %
                    (arg, type(arg).__name__))
        for kw, arg in kwargs.items():
            if isinstance(arg, str) or callable(arg):
                expanded_kwargs[kw] = arg
            else:
                raise TypeError(
                    "Cannot expand kwarg %r, must be str or "\
                    "callable, not" % (arg, type(arg).__name__))
        # next, resolve rule names to callables
        for name, rule in (_resolve_rule_name(a) for a in expanded_args):
            self.rules[name] = rule
            self.rules_names.append(name)
        for name, rule in (_resolve_rule_name(a, k) for k, a in expanded_kwargs.items()):
            self.rules[name] = rule
            self.rules_names.append(name)
        
    def apply_single_rule(self, rulename, text):
        if rulename not in self.rules:
            raise ValueError("Rule %s is not found in active rules" % rulename)
        try:
            res = self.rules[rulename](text)
        except ValueError as e:
            raise ValueError("Rule %s failed to apply: %s" % (rulename, e))
        return res
    
    def apply(self, text):
        for rule in self.rules_names:
            text = self.apply_single_rule(rule, text)
        return text
        
    def __call__(self, text):
        return self.apply(text)

def typography(text):
    t = Typography(STANDARD_RULES)
    return t.apply(text)

if __name__ == '__main__':
    from pytils.test import run_tests_from_module, test_typo
    run_tests_from_module(test_typo, verbosity=2)
    

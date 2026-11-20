import random
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tools import pycompat


def Random(seed):
    """ Return a random number generator object with the given seed. """
    r = random.Random()
    r.seed(seed, version=2)
    return r


def format_str(val, counter, values):
    """ Format the given value (with method ``format``) when it is a string. """
    if isinstance(val, str):
        return val.format(counter=counter, values=values)
    return val


def chain_factories(field_factories, model_name):
    """ Instantiate a generator by calling all the field factories. """
    generator = root_factory()
    for (fname, field_factory) in field_factories:
        generator = field_factory(generator, fname, model_name)
    return generator


def root_factory():
    """ Return a generator with empty values dictionaries (except for the flag ``__complete``). """
    yield {'__complete': False}
    while True:
        yield {'__complete': True}


def randomize(vals, weights=None, seed=False, formatter=format_str, counter_offset=0):
    """ Return a factory for an iterator of values dicts with pseudo-randomly
    chosen values (among ``vals``) for a field.

    :param list vals: list in which a value will be chosen, depending on `weights`
    :param list weights: list of probabilistic weights
    :param seed: optional initialization of the random number generator
    :param function formatter: (val, counter, values) --> formatted_value
    :param int counter_offset:
    :returns: function of the form (iterator, field_name, model_name) -> values
    :rtype: function (iterator, str, str) -> dict
    """
    def generate(iterator, field_name, model_name):
        r = Random('%s+field+%s' % (model_name, seed or field_name))
        for counter, values in enumerate(iterator):
            val = r.choices(vals, weights)[0]
            values[field_name] = formatter(val, counter + counter_offset, values)
            yield values
    return generate


def cartesian(vals, weights=None, seed=False, formatter=format_str, then=None):
    """ Return a factory for an iterator of values dicts that combines all ``vals`` for
    the field with the other field values in input.

    :param list vals: list in which a value will be chosen, depending on `weights`
    :param list weights: list of probabilistic weights
    :param seed: optional initialization of the random number generator
    :param function formatter: (val, counter, values) --> formatted_value
    :param function then: if defined, factory used when vals has been consumed.
    :returns: function of the form (iterator, field_name, model_name) -> values
    :rtype: function (iterator, str, str) -> dict
    """
    def generate(iterator, field_name, model_name):
        counter = 0
        for values in iterator:
            if values['__complete']:
                break  # will consume and lose an element, (complete so a filling element). If it is a problem, use peekable instead.
            for val in vals:
                yield {**values, field_name: formatter(val, counter, values)}
            counter += 1
        factory = then or randomize(vals, weights, seed, formatter, counter)
        yield from factory(iterator, field_name, model_name)
    return generate


def iterate(vals, weights=None, seed=False, formatter=format_str, then=None):
    """ Return a factory for an iterator of values dicts that picks a value among ``vals``
    for each input.  Once all ``vals`` have been used once, resume as ``then`` or as a
    ``randomize`` generator.

    :param list vals: list in which a value will be chosen, depending on `weights`
    :param list weights: list of probabilistic weights
    :param seed: optional initialization of the random number generator
    :param function formatter: (val, counter, values) --> formatted_value
    :param function then: if defined, factory used when vals has been consumed.
    :returns: function of the form (iterator, field_name, model_name) -> values
    :rtype: function (iterator, str, str) -> dict
    """
    def generate(iterator, field_name, model_name):
        counter = 0
        for val in vals: # iteratable order is important, shortest first
            values = next(iterator)
            values[field_name] = formatter(val, counter, values)
            values['__complete'] = False
            yield values
            counter += 1
        factory = then or randomize(vals, weights, seed, formatter, counter)
        yield from factory(iterator, field_name, model_name)
    return generate


def constant(val, formatter=format_str):
    """ Return a factory for an iterator of values dicts that sets the field
    to the given value in each input dict.

    :returns: function of the form (iterator, field_name, model_name) -> values
    :rtype: function (iterator, str, str) -> dict
    """
    def generate(iterator, field_name, _):
        for counter, values in enumerate(iterator):
            values[field_name] = formatter(val, counter, values)
            yield values
    return generate


def compute(function, seed=None):
    """ Return a factory for an iterator of values dicts that computes the field value
    as ``function(values, counter, random)``, where ``values`` is the other field values,
    ``counter`` is an integer, and ``random`` is a pseudo-random number generator.

    :param callable function: (values, counter, random) --> field_values
    :param seed: optional initialization of the random number generator
    :returns: function of the form (iterator, field_name, model_name) -> values
    :rtype: function (iterator, str, str) -> dict
    """
    def generate(iterator, field_name, model_name):
        r = Random('%s+field+%s' % (model_name, seed or field_name))
        for counter, values in enumerate(iterator):
            val = function(values=values, counter=counter, random=r)
            values[field_name] = val
            yield values
    return generate

def randint(a, b, seed=None):
    """ Return a factory for an iterator of values dicts that sets the field
    to a random integer between a and b included in each input dict.

    :param int a: minimal random value
    :param int b: maximal random value
    :param int seed:
    :returns: function of the form (iterator, field_name, model_name) -> values
    :rtype: function (iterator, str, str) -> dict
    """
    def get_rand_int(random=None, **kwargs):
        return random.randint(a, b)
    return compute(get_rand_int, seed=seed)

def randfloat(a, b, seed=None):
    """ Return a factory for an iterator of values dicts that sets the field
    to a random float between a and b included in each input dict.
    """
    def get_rand_float(random=None, **kwargs):
        return random.uniform(a, b)
    return compute(get_rand_float, seed=seed)

def randdatetime(*, base_date=None, relative_before=None, relative_after=None, seed=None):
    """ Return a factory for an iterator of values dicts that sets the field
    to a random datetime between relative_before and relative_after, relatively to
    base_date

    :param datetime base_date: override the default base date if needed.
    :param relativedelta|timedelta relative_after: range up which we can go after the
         base date. If not set, defaults to 0, i.e. only in the past of reference.
    :param relativedelta|timedelta relative_before: range up which we can go before the
         base date. If not set, defaults to 0, i.e. only in the future of reference.
    :param seed:
    :return: iterator for random dates inside the defined range
    """
    base_date = base_date or datetime(2020, 1, 1)
    seconds_before = relative_before and ((base_date + relative_before) - base_date).total_seconds() or 0
    seconds_after = relative_after and ((base_date + relative_after) - base_date).total_seconds() or 0

    def get_rand_datetime(random=None, **kwargs):
        return base_date + relativedelta(seconds=random.randint(int(seconds_before), int(seconds_after)))
    return compute(get_rand_datetime, seed=seed)

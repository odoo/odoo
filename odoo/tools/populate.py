import random
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
    """ Instanciate a generator by calling all the field factories. """
    generator = root_factory()
    for (fname, field_factory) in field_factories:
        generator = field_factory(generator, fname, model_name)
    return generator


def root_factory():
    """ Return a generator with empty values dictionaries (except for the flag ``__complete``). """
    yield {'__complete': False}
    while True:
        yield {'__complete': True}


def randomize(vals, weights=None, seed=False, formater=format_str):
    """ Return a factory for an iterator of values dicts with pseudo-randomly
    chosen values (among ``vals``) for a field.
    """
    def generate(iterator, field_name, model_name, counter_offset=0):
        r = Random(seed or '%s+field+%s' % (model_name, field_name))
        for counter, values in enumerate(iterator):
            val = r.choices(vals, weights)[0]
            values[field_name] = formater(val, counter+counter_offset, values)
            yield values
    return generate


def cartesian(vals, weights=None, seed=False, formater=format_str):
    """ Return a factory for an iterator of values dicts that combines all ``vals`` for
    the field with the other field values in input.
    """
    def generate(iterator, field_name, model_name):
        counter = 0
        for values in iterator:
            if values['__complete']:
                break  # will consume and lose an element, (complete so a filling element). If it is a problem, use peekable instead.
            for val in vals:
                yield {**values, field_name: formater(val, counter, values)}
            counter += 1
        yield from randomize(vals, weights, seed, formater)(iterator, field_name, model_name, counter)
    return generate


def iterate(vals, weights=None, seed=False, formater=format_str):
    def generate(iterator, field_name, model_name):
        counter = 0
        for val in vals: # iteratable order is important, shortest first
            values = next(iterator)
            values[field_name] = formater(val, counter, values)
            values['__complete'] = False
            yield values
            counter += 1
        yield from randomize(vals, weights, seed, formater)(iterator, field_name, model_name, counter)
    return generate


def constant(val, formater=format_str):
    def generate(iterator, field_name, _):
        counter = 0
        for values in iterator:
            values[field_name] = formater(val, counter, values)
            yield values
            counter += 1
    return generate


def compute(function, seed=None):
    def generate(iterator, field_name, model_name):
        r = Random(seed or '%s+%s' % (model_name, field_name))
        for counter, values in enumerate(iterator):
            val = function(values=values, counter=counter, random=r)
            values[field_name] = val
            yield values
    return generate

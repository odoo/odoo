SET_STATE_MAPPING = {
    'pending': {
        'a': ('draft',),
        't': 'pending',
    },
    'authorized': {
        'a': ('draft', 'pending',),
        't': 'authorized',
    },
    'done': {
        'a': ('draft', 'pending', 'authorized', 'error',),
        't': 'done',
    },
    'canceled': {
        'a': ('draft', 'pending', 'authorized'),
        't': 'cancel',
    },
    'error': {
        'a': ('draft', 'pending', 'authorized', 'done',),
        't': 'error',
    },
}

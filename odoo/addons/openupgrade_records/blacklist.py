BLACKLIST_MODULES = [
    # the hw_* modules are not affected by a migration as they don't
    # contain any ORM functionality, but they do start up threads that
    # delay the process and spit out annoying log messages continously.
    'hw_escpos',
    'hw_proxy',
    'hw_scale',
    'hw_scanner',
]

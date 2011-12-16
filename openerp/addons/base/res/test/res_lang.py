import sys
import openerp

# TODO this loop will be exposed as open_openerp_namespace()
# once trunk-cleaning-vmt is merged.
for k, v in list(sys.modules.items()):
        if k.startswith('openerp.') and sys.modules.get(k[8:]) is None:
            sys.modules[k[8:]] = v

import openerp.addons.base.res.res_lang as res_lang
res_lang._group_examples()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

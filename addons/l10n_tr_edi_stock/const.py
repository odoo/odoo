# GİB mailbox (Posta Kutusu) receiving an e-Dispatch whose receiver has no e-Dispatch alias
GIB_EDISPATCH_ALIAS = 'urn:mail:irsaliyepk@gib.gov.tr'

# l10n_tr_edi.document state of the e-Dispatch -> stock.picking send status
DOCUMENT_STATE_TO_DISPATCH_STATUS = {
    'sent': 'sent',
    'waiting': 'waiting',
    'accepted': 'succeed',
    'error': 'error',
}

# l10n_tr_edi.document state of the e-Dispatch answer -> stock.picking response status
DOCUMENT_STATE_TO_RESPONSE_STATUS = {
    'sent': 'sent',
    'waiting': 'waiting',
    'error': 'error',
    'accepted': 'accepted',
    'accepted_automatically': 'accepted_automatically',
    'rejected': 'rejected',
}

# Response statuses of an e-Dispatch answer that GİB will not change anymore
RESPONSE_SETTLED_STATUSES = {'accepted', 'accepted_automatically', 'rejected'}

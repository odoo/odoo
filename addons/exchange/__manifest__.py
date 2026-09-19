{
    "name": "Exchange",
    "version": "19.0.1.0.1",
    "category": "Hidden",
    "sequence": 6,
    "summary": "Channels, transmissions and protocols for document exchange with an outside party",
    "description": """
Exchange
========

The conversation with a counterparty, once, for every party that has one.

`odoo.libs.documents` answers what a document *is*. This answers who we are
sending it to, whether it arrived, what the answer was, and when to ask again.

Models
------
* ``exchange.channel`` -- who. Delegates to ``integration.service`` for
  transport, ``credential.credential`` for secrets and
  ``certificate.certificate`` for signing material, so none of the three is
  restated here.
* ``exchange.transmission`` -- what happened. One row per ask, carrying the
  *verdict* lifecycle. The transport lifecycle stays on ``integration.exchange``,
  which this points at: an HTTP 200 carrying a rejection is a transport
  success and a business rejection, and one Selection cannot be both.
* ``exchange.protocol`` -- how. An ``AbstractModel`` registry, one concrete
  model per counterparty, implementing six methods.
* ``mixin.exchange.subject`` -- what a business record carries.

Lifecycle
---------
``intent`` is what we are asking for -- issue, annul, amend, query.
``state`` is where that ask has got to -- draft, queued, sent, accepted,
rejected, expired. They are separate fields because they are separate facts:
an annulment that failed is ``intent=annul, state=rejected``, not a value in
the issuing field.

An exchange has a counterparty, a lifecycle and a journal, and none of the
three is a localisation.
""",
    "author": "AgroMarin",
    "license": "LGPL-3",
    "depends": [
        "integration",
        "certificate",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "views/exchange_channel_views.xml",
        "views/exchange_transmission_views.xml",
        "views/exchange_menus.xml",
        "data/ir_cron.xml",
    ],
}

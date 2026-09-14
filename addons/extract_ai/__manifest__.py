{
    "name": "Document Extraction - AI Readers",
    "version": "19.0.1.0.0",
    "category": "Hidden",
    "summary": "Generative strategies for extract, on the gateway_ml registry",
    "description": """
Document Extraction - AI Readers
================================

Two generative strategies for ``extract``, both reaching a model
through ``gateway_ml`` -- its provider registry, its selection by cost or accuracy,
its fallback chain, its per-vendor clients. Neither knows a vendor's name.

``llm_text``
    Reads the document's own text. Needs no vision-capable model, so the
    cheapest model a company holds a key for can serve it.

``llm_vision``
    Looks at the rendered page, for a document that carries no text.

Splitting them is the point. ``api_ocr`` had one generative path and sent a
rendered page to a vision model whether or not the document carried its own
text -- the expensive way to read characters somebody already wrote down. Now
only a scan reaches a vision model.

The prompt is generated from the schema
-------------------------------------
``api_ocr`` carried six document processors, each a hand-written prompt beside
a hand-written JSON example, saying the same thing six times in six voices. A
schema already declares its fields, their types, which are required and what
they mean, which is a prompt in a form a machine can keep consistent. Adding a
document type is registering a schema; a localization that extends a schema
extends every prompt that uses it, in the same commit.

Both strategies run last and answer only what the cheaper ones could not read,
so an escalation asks about two missing fields rather than re-reading a whole
bill.
    """,
    "author": "AgroMarin",
    "website": "https://agromarin.com",
    "license": "LGPL-3",
    "depends": [
        "gateway_ml",
        "extract",
    ],
}

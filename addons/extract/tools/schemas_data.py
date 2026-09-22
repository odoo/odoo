from .schema import FieldSpec, not_after, register_schema, sums_to

_MONEY = "float"

register_schema(
    "invoice",
    fields={
        "vendor_name": FieldSpec("str", help="Legal name of the issuer"),
        "vendor_vat": FieldSpec("str", help="Tax identifier of the issuer"),
        "invoice_number": FieldSpec("str"),
        "invoice_date": FieldSpec("date", required=True),
        "due_date": FieldSpec("date"),
        "currency": FieldSpec("str"),
        "subtotal": FieldSpec(_MONEY),
        "tax_amount": FieldSpec(_MONEY),
        "total": FieldSpec(_MONEY, required=True),
        "lines": FieldSpec(
            "list",
            items={
                "description": FieldSpec("str", required=True),
                "quantity": FieldSpec("float"),
                "unit_price": FieldSpec(_MONEY),
                "amount": FieldSpec(_MONEY),
            },
        ),
    },
    rules=[
        sums_to("invoice_totals", ("subtotal", "tax_amount"), "total"),
        not_after("invoice_dates", "invoice_date", "due_date"),
    ],
)

register_schema(
    "receipt",
    fields={
        "merchant_name": FieldSpec("str", required=True),
        "date": FieldSpec("date", required=True),
        "currency": FieldSpec("str"),
        "subtotal": FieldSpec(_MONEY),
        "tax_amount": FieldSpec(_MONEY),
        "tip_amount": FieldSpec(_MONEY),
        "total": FieldSpec(_MONEY, required=True),
        "payment_method": FieldSpec("str"),
        "items": FieldSpec(
            "list",
            items={
                "description": FieldSpec("str", required=True),
                "quantity": FieldSpec("float"),
                "unit_price": FieldSpec(_MONEY),
                "amount": FieldSpec(_MONEY),
            },
        ),
    },
    rules=[
        sums_to("receipt_totals", ("subtotal", "tax_amount", "tip_amount"), "total")
    ],
)

register_schema(
    "utility_bill",
    fields={
        "provider": FieldSpec("str"),
        "account": FieldSpec("str"),
        "period_start": FieldSpec("date"),
        "period_end": FieldSpec("date"),
        "due_date": FieldSpec("date"),
        "currency": FieldSpec("str"),
        "subtotal": FieldSpec(_MONEY),
        "tax_amount": FieldSpec(_MONEY),
        "total": FieldSpec(_MONEY, required=True),
        "consumption": FieldSpec("float"),
        "consumption_unit": FieldSpec("str"),
    },
    rules=[not_after("utility_period", "period_start", "period_end")],
)

register_schema(
    "bank_statement",
    fields={
        "bank_name": FieldSpec("str"),
        "account": FieldSpec("str"),
        "period_start": FieldSpec("date"),
        "period_end": FieldSpec("date"),
        "currency": FieldSpec("str"),
        "opening_balance": FieldSpec(_MONEY),
        "closing_balance": FieldSpec(_MONEY),
        "transactions": FieldSpec(
            "list",
            required=True,
            items={
                "date": FieldSpec("date"),
                "description": FieldSpec("str", required=True),
                "amount": FieldSpec(_MONEY, required=True),
            },
        ),
    },
    rules=[not_after("statement_period", "period_start", "period_end")],
)

register_schema(
    "id_document",
    fields={
        "full_name": FieldSpec("str", required=True),
        "document_number": FieldSpec("str", required=True),
        "date_of_birth": FieldSpec("date"),
        "expiry_date": FieldSpec("date"),
        "nationality": FieldSpec("str"),
        "issuer": FieldSpec("str"),
    },
)

register_schema(
    "business_card",
    fields={
        "cards": FieldSpec(
            "list",
            required=True,
            help="One row per business card in the image",
            items={
                "person_name": FieldSpec("str"),
                "company_name": FieldSpec("str"),
                "job_title": FieldSpec("str"),
                "email": FieldSpec("str", help="The main email address"),
                "phone": FieldSpec("str", help="The main phone number"),
                "website": FieldSpec("str"),
                "street": FieldSpec(
                    "str", help="The first line of the address: street and number"
                ),
                "street2": FieldSpec(
                    "str", help="The second line of the address, if it has two"
                ),
                "city": FieldSpec("str"),
                "zip": FieldSpec("str"),
                "state_code": FieldSpec(
                    "str", help="The state's code, not its name; left out if unknown"
                ),
                "country_code": FieldSpec(
                    "str", help="The country's two-letter ISO code; left out if unknown"
                ),
            },
        ),
    },
    instructions=(
        "You read the images of business cards. Report only the text printed on "
        "a card; never guess, and leave out whatever the card does not show. A "
        "card that names neither a person nor a company is not reported."
    ),
)

register_schema(
    "resume",
    fields={
        "full_name": FieldSpec("str", required=True),
        "email": FieldSpec("str"),
        "phone": FieldSpec("str"),
        "summary": FieldSpec("str"),
        "experience": FieldSpec(
            "list",
            items={
                "employer": FieldSpec("str", required=True),
                "title": FieldSpec("str"),
                "start_date": FieldSpec("date"),
                "end_date": FieldSpec("date"),
                "summary": FieldSpec("str"),
            },
        ),
        "education": FieldSpec(
            "list",
            items={
                "institution": FieldSpec("str", required=True),
                "qualification": FieldSpec("str"),
                "start_date": FieldSpec("date"),
                "end_date": FieldSpec("date"),
            },
        ),
        "skills": FieldSpec(
            "list",
            items={
                "name": FieldSpec("str", required=True),
                "level": FieldSpec("str"),
            },
        ),
    },
)

register_schema(
    "generic",
    fields={
        "title": FieldSpec("str"),
        "text": FieldSpec("str", required=True),
        "language": FieldSpec("str"),
        "entities": FieldSpec("dict"),
    },
)

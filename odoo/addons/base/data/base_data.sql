-------------------------------------------------------------------------
-- Pure SQL
-------------------------------------------------------------------------

CREATE TABLE ir_actions (id serial primary key);
CREATE TABLE ir_act_window (primary key(id)) INHERITS (ir_actions);
CREATE TABLE ir_act_report_xml (primary key(id)) INHERITS (ir_actions);
CREATE TABLE ir_act_url (primary key(id)) INHERITS (ir_actions);
CREATE TABLE ir_act_server (primary key(id)) INHERITS (ir_actions);
CREATE TABLE ir_act_client (primary key(id)) INHERITS (ir_actions);

CREATE TABLE res_currency (
    id integer primary key generated always as identity,
    name varchar NOT NULL,
    symbol varchar NOT NULL
);

CREATE TABLE res_company (
    id integer primary key generated always as identity,
    name varchar NOT NULL,
    partner_id integer,
    currency_id integer references res_currency,
    sequence integer,
    create_date timestamp without time zone
);

CREATE TABLE res_partner (
    id integer primary key generated always as identity,
    company_id integer references res_company,
    create_date timestamp without time zone,
    name varchar
);

CREATE TABLE res_users (
    id integer primary key generated always as identity,
    company_id integer references res_company,
    partner_id integer references res_partner,
    active boolean default true,
    create_date timestamp without time zone,
    login varchar(64) NOT NULL UNIQUE,
    password varchar default null
);

CREATE TABLE res_groups (
    id integer primary key generated always as identity,
    name jsonb NOT NULL
);

CREATE TABLE ir_module_category (
    id integer primary key generated always as identity,
    create_uid integer references res_users on delete set null,
    create_date timestamp without time zone,
    write_date timestamp without time zone,
    write_uid integer references res_users on delete set null,
    parent_id integer REFERENCES ir_module_category ON DELETE SET NULL,
    name jsonb NOT NULL
);

CREATE TABLE ir_module_module (
    id integer primary key generated always as identity,
    create_uid integer references res_users on delete set null,
    create_date timestamp without time zone,
    write_date timestamp without time zone,
    write_uid integer references res_users on delete set null,
    website character varying,
    summary jsonb,
    name character varying NOT NULL,
    author character varying,
    icon varchar,
    state character varying(16),
    latest_version character varying,
    shortdesc jsonb,
    category_id integer REFERENCES ir_module_category ON DELETE SET NULL,
    description jsonb,
    application boolean default false,
    demo boolean default False,
    web boolean DEFAULT FALSE,
    license character varying(32),
    sequence integer DEFAULT 100,
    auto_install boolean default false,
    to_buy boolean default False
);

CREATE TABLE ir_module_module_dependency (
    id integer primary key generated always as identity,
    name character varying,
    module_id integer REFERENCES ir_module_module ON DELETE cascade,
    auto_install_required boolean DEFAULT true
);

CREATE TABLE ir_model_data (
    id integer primary key generated always as identity,
    create_uid integer,
    create_date timestamp without time zone DEFAULT (now() at time zone 'UTC'),
    write_date timestamp without time zone DEFAULT (now() at time zone 'UTC'),
    write_uid integer,
    res_id integer,
    noupdate boolean DEFAULT false,
    name varchar NOT NULL,
    module varchar NOT NULL,
    model varchar NOT NULL
);

----------------------
-- Mandatory base data
----------------------
WITH
    currency AS (INSERT INTO res_currency (name, symbol) VALUES ('USD', '$') RETURNING id),
    "group" AS (INSERT INTO res_groups (name) VALUES ('{"en_US": "Employee"}') RETURNING id),
    company AS (
        INSERT INTO res_company (name, partner_id, currency_id, create_date)
        VALUES ('My Company', 1, (SELECT id FROM currency), now() at time zone 'UTC')
        RETURNING id
    ),
    partner AS (
        INSERT INTO res_partner (name, company_id, create_date)
        VALUES ('My Company', (SELECT id FROM company), now() at time zone 'UTC')
        RETURNING id
    ),
    "user" AS (
        INSERT INTO res_users (login, active, partner_id, company_id, create_date)
        VALUES ('__system__', false, (SELECT id FROM partner), (SELECT id FROM company), now() at time zone 'UTC')
        RETURNING id
    )
INSERT INTO ir_model_data (module, name, model, noupdate, res_id)
VALUES
    ('base', 'USD', 'res.currency', true, (SELECT id FROM currency)),
    ('base', 'main_company', 'res.company', true, (SELECT id FROM company)),
    ('base', 'main_partner', 'res.partner', true, (SELECT id FROM partner)),
    ('base', 'user_root', 'res.users', true, (SELECT id FROM "user")),
    ('base', 'group_user', 'res.groups', true, (SELECT id FROM "group"));

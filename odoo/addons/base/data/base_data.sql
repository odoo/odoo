-------------------------------------------------------------------------
-- Pure SQL
-------------------------------------------------------------------------

CREATE TABLE ir_actions (
  id serial,
  primary key(id)
);
CREATE TABLE ir_act_window (primary key(id)) INHERITS (ir_actions);
CREATE TABLE ir_act_report_xml (primary key(id)) INHERITS (ir_actions);
CREATE TABLE ir_act_url (primary key(id)) INHERITS (ir_actions);
CREATE TABLE ir_act_server (primary key(id)) INHERITS (ir_actions);
CREATE TABLE ir_act_client (primary key(id)) INHERITS (ir_actions);

CREATE TABLE res_users (
    id serial NOT NULL,
    active boolean default True,
    login varchar(64) NOT NULL UNIQUE,
    password varchar default null,
    -- No FK references below, will be added later by ORM
    -- (when the destination rows exist)
    company_id integer, -- references res_company,
    partner_id integer, -- references res_partner,
    create_date timestamp without time zone,
    primary key(id)
);

CREATE TABLE res_groups (
    id serial NOT NULL,
    name varchar NOT NULL,
    primary key(id)
);

CREATE TABLE ir_module_category (
    id serial NOT NULL,
    create_uid integer, -- references res_users on delete set null,
    create_date timestamp without time zone,
    write_date timestamp without time zone,
    write_uid integer, -- references res_users on delete set null,
    parent_id integer REFERENCES ir_module_category ON DELETE SET NULL,
    name character varying NOT NULL,
    primary key(id)
);

CREATE TABLE ir_module_module (
    id serial NOT NULL,
    create_uid integer, -- references res_users on delete set null,
    create_date timestamp without time zone,
    write_date timestamp without time zone,
    write_uid integer, -- references res_users on delete set null,
    website character varying,
    summary character varying,
    name character varying NOT NULL,
    author character varying,
    icon varchar,
    state character varying(16),
    latest_version character varying,
    shortdesc character varying,
    category_id integer REFERENCES ir_module_category ON DELETE SET NULL,
    description text,
    application boolean default False,
    demo boolean default False,
    web boolean DEFAULT FALSE,
    license character varying(32),
    sequence integer DEFAULT 100,
    auto_install boolean default False,
    to_buy boolean default False,
    primary key(id)
);
ALTER TABLE ir_module_module add constraint name_uniq unique (name);

CREATE TABLE ir_module_module_dependency (
    id serial NOT NULL,
    create_uid integer, -- references res_users on delete set null,
    create_date timestamp without time zone,
    write_date timestamp without time zone,
    write_uid integer, -- references res_users on delete set null,
    name character varying,
    module_id integer REFERENCES ir_module_module ON DELETE cascade,
    auto_install_required boolean DEFAULT true,
    primary key(id)
);

CREATE TABLE ir_model_data (
    id serial NOT NULL,
    create_uid integer,
    create_date timestamp without time zone DEFAULT (now() at time zone 'UTC'),
    write_date timestamp without time zone DEFAULT (now() at time zone 'UTC'),
    write_uid integer,
    noupdate boolean DEFAULT False,
    name varchar NOT NULL,
    module varchar NOT NULL,
    model varchar NOT NULL,
    res_id integer,
    primary key(id)
);

CREATE TABLE res_currency (
    id serial,
    name varchar NOT NULL,
    symbol varchar NOT NULL,
    primary key(id)
);

CREATE TABLE res_company (
    id serial,
    name varchar NOT NULL,
    partner_id integer,
    currency_id integer,
    sequence integer,
    create_date timestamp without time zone,
    primary key(id)
);

CREATE TABLE res_partner (
    id serial,
    name varchar,
    company_id integer,
    create_date timestamp without time zone,
    primary key(id)
);


---------------------------------
-- Default data
---------------------------------
insert into res_currency (id, name, symbol) VALUES (1, 'EUR', '€');
insert into ir_model_data (name, module, model, noupdate, res_id) VALUES ('EUR', 'base', 'res.currency', true, 1);
select setval('res_currency_id_seq', 1);

insert into res_company (id, name, partner_id, currency_id, create_date) VALUES (1, 'My Company', 1, 1, now() at time zone 'UTC');
insert into ir_model_data (name, module, model, noupdate, res_id) VALUES ('main_company', 'base', 'res.company', true, 1);
select setval('res_company_id_seq', 1);

insert into res_partner (id, name, company_id, create_date) VALUES (1, 'My Company', 1, now() at time zone 'UTC');
insert into ir_model_data (name, module, model, noupdate, res_id) VALUES ('main_partner', 'base', 'res.partner', true, 1);
select setval('res_partner_id_seq', 1);

insert into res_users (id, login, password, active, partner_id, company_id, create_date) VALUES (1, '__system__', NULL, false, 1, 1, now() at time zone 'UTC');
insert into ir_model_data (name, module, model, noupdate, res_id) VALUES ('user_root', 'base', 'res.users', true, 1);
select setval('res_users_id_seq', 1);

insert into res_groups (id, name) VALUES (1, 'Employee');
insert into ir_model_data (name, module, model, noupdate, res_id) VALUES ('group_user', 'base', 'res.groups', true, 1);
select setval('res_groups_id_seq', 1);

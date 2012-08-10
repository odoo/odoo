-------------------------------------------------------------------------
-- Pure SQL
-------------------------------------------------------------------------

-------------------------------------------------------------------------
-- IR dictionary
-------------------------------------------------------------------------

create table ir_values
(
    id serial,
    name varchar(128) not null,
    key varchar(128) not null,
    key2 varchar(256) not null,
    model varchar(128) not null,
    value text,
    meta text default NULL,
    res_id integer default null,
    primary key (id)
);

-------------------------------------------------------------------------
-- Modules Description
-------------------------------------------------------------------------

CREATE TABLE ir_model (
  id serial,
  model varchar(64) DEFAULT ''::varchar NOT NULL,
  name varchar(64),
  state varchar(16),
  info text,
  primary key(id)
);

CREATE TABLE ir_model_fields (
  id serial,
  model varchar(64) DEFAULT ''::varchar NOT NULL,
  model_id int references ir_model on delete cascade,
  name varchar(64) DEFAULT ''::varchar NOT NULL,
  relation varchar(64),
  select_level varchar(4),
  field_description varchar(256),
  ttype varchar(64),
  state varchar(64) default 'base',
  view_load boolean,
  relate boolean default False,
  relation_field varchar(128),
  translate boolean default False,
  primary key(id)
);

ALTER TABLE ir_model_fields ADD column serialization_field_id int references ir_model_fields on delete cascade;


-------------------------------------------------------------------------
-- Actions
-------------------------------------------------------------------------

CREATE TABLE ir_actions (
    id serial NOT NULL,
    name varchar(64) DEFAULT ''::varchar NOT NULL,
    "type" varchar(32) NOT NULL,
    usage varchar(32) DEFAULT null,
    primary key(id)
);

CREATE TABLE ir_act_window (
    view_id integer,
    res_model varchar(64),
    view_type varchar(16),
    "domain" varchar(250),
    primary key(id)
)
INHERITS (ir_actions);

CREATE TABLE ir_act_report_xml (
    model varchar(64) NOT NULL,
    report_name varchar(64) NOT NULL,
    report_xsl varchar(256),
    report_xml varchar(256),
    auto boolean default true,
    primary key(id)
)
INHERITS (ir_actions);

create table ir_act_report_custom (
    report_id int,
--  report_id int references ir_report_custom
    primary key(id)
)
INHERITS (ir_actions);

CREATE TABLE ir_act_wizard (
    wiz_name varchar(64) NOT NULL,
    primary key(id)
)
INHERITS (ir_actions);

CREATE TABLE ir_act_url (
    url text NOT NULL,
    target varchar(64) NOT NULL,
    primary key(id)
)
INHERITS (ir_actions);

CREATE TABLE ir_act_server (
    primary key(id)
)
INHERITS (ir_actions);

CREATE TABLE ir_act_client (
    primary key(id)
)
INHERITS (ir_actions);


CREATE TABLE ir_ui_view (
    id serial NOT NULL,
    name varchar(64) DEFAULT ''::varchar NOT NULL,
    model varchar(64) DEFAULT ''::varchar NOT NULL,
    "type" varchar(64) DEFAULT 'form'::varchar NOT NULL,
    arch text NOT NULL,
    field_parent varchar(64),
    priority integer DEFAULT 5 NOT NULL,
    primary key(id)
);

CREATE TABLE ir_ui_menu (
    id serial NOT NULL,
    parent_id int references ir_ui_menu on delete set null,
    name varchar(64) DEFAULT ''::varchar NOT NULL,
    icon varchar(64) DEFAULT ''::varchar,
    primary key (id)
);

select setval('ir_ui_menu_id_seq', 2);

---------------------------------
-- Res users
---------------------------------

-- level:
--   0  RESTRICT TO USER
--   1  RESTRICT TO GROUP
--   2  PUBLIC

CREATE TABLE res_users (
    id serial NOT NULL,
    name varchar(64) not null,
    active boolean default True,
    login varchar(64) NOT NULL UNIQUE,
    password varchar(64) default null,
    tz varchar(64) default null,
    lang varchar(64) default '',
    -- No FK references below, will be added later by ORM
    -- (when the destination rows exist)
    company_id int,
    primary key(id)
);
alter table res_users add constraint res_users_login_uniq unique (login);

CREATE TABLE res_groups (
    id serial NOT NULL,
    name varchar(64) NOT NULL,
    primary key(id)
);

CREATE TABLE res_groups_users_rel (
    uid integer NOT NULL references res_users on delete cascade,
    gid integer NOT NULL references res_groups on delete cascade,
    UNIQUE("uid","gid")
);

create index res_groups_users_rel_uid_idx on res_groups_users_rel (uid);
create index res_groups_users_rel_gid_idx on res_groups_users_rel (gid);


---------------------------------
-- Workflows
---------------------------------

create table wkf
(
    id serial,
    name varchar(64),
    osv varchar(64),
    on_create bool default False,
    primary key(id)
);

create table wkf_activity
(
    id serial,
    wkf_id int references wkf on delete cascade,
    subflow_id int references wkf on delete set null,
    split_mode varchar(3) default 'XOR',
    join_mode varchar(3) default 'XOR',
    kind varchar(16) not null default 'dummy',
    name varchar(64),
    signal_send varchar(32) default null,
    flow_start boolean default False,
    flow_stop boolean default False,
    action text default null,
    primary key(id)
);

create table wkf_transition
(
    id serial,
    act_from int references wkf_activity on delete cascade,
    act_to int references wkf_activity on delete cascade,
    condition varchar(128) default NULL,

    trigger_type varchar(128) default NULL,
    trigger_expr_id varchar(128) default NULL,

    signal varchar(64) default null,
    group_id int references res_groups on delete set null,

    primary key(id)
);

create table wkf_instance
(
    id serial,
    wkf_id int references wkf on delete restrict,
    uid int default null,
    res_id int not null,
    res_type varchar(64) not null,
    state varchar(32) not null default 'active',
    primary key(id)
);

create table wkf_workitem
(
    id serial,
    act_id int not null references wkf_activity on delete cascade,
    inst_id int not null references wkf_instance on delete cascade,
    subflow_id int references wkf_instance on delete cascade,
    state varchar(64) default 'blocked',
    primary key(id)
);

create table wkf_witm_trans
(
    trans_id int not null references wkf_transition on delete cascade,
    inst_id int not null references wkf_instance on delete cascade
);

create index wkf_witm_trans_inst_idx on wkf_witm_trans (inst_id);

create table wkf_logs
(
    id serial,
    res_type varchar(128) not null,
    res_id int not null,
    uid int references res_users on delete set null,
    act_id int references wkf_activity on delete set null,
    time time not null,
    info varchar(128) default NULL,
    primary key(id)
);

---------------------------------
-- Modules
---------------------------------

CREATE TABLE ir_module_category (
    id serial NOT NULL,
    create_uid integer references res_users on delete set null,
    create_date timestamp without time zone,
    write_date timestamp without time zone,
    write_uid integer references res_users on delete set null,
    parent_id integer REFERENCES ir_module_category ON DELETE SET NULL,
    name character varying(128) NOT NULL,
    primary key(id)
);


CREATE TABLE ir_module_module (
    id serial NOT NULL,
    create_uid integer references res_users on delete set null,
    create_date timestamp without time zone,
    write_date timestamp without time zone,
    write_uid integer references res_users on delete set null,
    website character varying(256),
    summary character varying(256),
    name character varying(128) NOT NULL,
    author character varying(128),
    url character varying(128),
    icon character varying(64),
    state character varying(16),
    latest_version character varying(64),
    shortdesc character varying(256),
    complexity character varying(32),
    category_id integer REFERENCES ir_module_category ON DELETE SET NULL,
    certificate character varying(64),
    description text,
    application boolean default False,
    demo boolean default False,
    web boolean DEFAULT FALSE,
    license character varying(32),
    sequence integer DEFAULT 100,
    auto_install boolean default False,
    primary key(id)
);
ALTER TABLE ir_module_module add constraint name_uniq unique (name);

CREATE TABLE ir_module_module_dependency (
    id serial NOT NULL,
    create_uid integer references res_users on delete set null,
    create_date timestamp without time zone,
    write_date timestamp without time zone,
    write_uid integer references res_users on delete set null,
    name character varying(128),
    version_pattern character varying(128) default NULL,
    module_id integer REFERENCES ir_module_module ON DELETE cascade,
    primary key(id)
);

CREATE TABLE res_company (
    id serial NOT NULL,
    name character varying(64) not null,
    parent_id integer references res_company on delete set null,
    primary key(id)
);

CREATE TABLE res_lang (
    id serial PRIMARY KEY,
    name VARCHAR(64) NOT NULL UNIQUE,
    code VARCHAR(16) NOT NULL UNIQUE
);

CREATE TABLE ir_model_data (
    id serial NOT NULL,
    create_uid integer,
    create_date timestamp without time zone,
    write_date timestamp without time zone,
    write_uid integer,
    noupdate boolean,
    name character varying(128) NOT NULL,
    date_init timestamp without time zone,
    date_update timestamp without time zone,
    module character varying(64) NOT NULL,
    model character varying(64) NOT NULL,
    res_id integer, primary key(id)
);

-- Records foreign keys and constraints installed by a module (so they can be
-- removed when the module is uninstalled):
--   - for a foreign key: type is 'f',
--   - for a constraint: type is 'u' (this is the convention PostgreSQL uses).
CREATE TABLE ir_model_constraint (
    id serial NOT NULL,
    create_uid integer,
    create_date timestamp without time zone,
    write_date timestamp without time zone,
    write_uid integer,
    date_init timestamp without time zone,
    date_update timestamp without time zone,
    module integer NOT NULL references ir_module_module on delete restrict,
    model integer NOT NULL references ir_model on delete restrict,
    type character varying(1) NOT NULL,
    name character varying(128) NOT NULL
);

-- Records relation tables (i.e. implementing many2many) installed by a module
-- (so they can be removed when the module is uninstalled).
CREATE TABLE ir_model_relation (
    id serial NOT NULL,
    create_uid integer,
    create_date timestamp without time zone,
    write_date timestamp without time zone,
    write_uid integer,
    date_init timestamp without time zone,
    date_update timestamp without time zone,
    module integer NOT NULL references ir_module_module on delete restrict,
    model integer NOT NULL references ir_model on delete restrict,
    name character varying(128) NOT NULL
);

---------------------------------
-- Users
---------------------------------

insert into res_users (id,login,password,name,active,company_id,lang) values (1,'admin','admin','Administrator',True,1,'en_US');
insert into ir_model_data (name,module,model,noupdate,res_id) values ('user_root','base','res.users',True,1);

-- Compatibility purpose, to remove V6.0
insert into ir_model_data (name,module,model,noupdate,res_id) values ('user_admin','base','res.users',True,1);

select setval('res_users_id_seq', 2);

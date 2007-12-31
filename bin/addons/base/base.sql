-------------------------------------------------------------------------
-- Pure SQL
-------------------------------------------------------------------------

CREATE TABLE perm (
    id serial NOT NULL,
    level smallint DEFAULT 4 NOT NULL,
    uid int default null,
    gid int default null,
    primary key(id)
);
insert into perm (id,uid,gid) values (1,1,1);

CREATE TABLE inherit (
    obj_type varchar(128) not null,
    obj_id int not null,
    inst_type varchar(128) not null,
    inst_id int not null
);

-------------------------------------------------------------------------
-- IR dictionary
-------------------------------------------------------------------------

create table ir_values
(
    id serial,
    perm_id int references perm on delete set null,
    name varchar(128) not null,
    key varchar(128) not null,
    key2 varchar(128) not null,
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
  perm_id int references perm on delete set null,
  model varchar(64) DEFAULT ''::varchar NOT NULL,
  name varchar(64),
  info text,
  primary key(id)
);

CREATE TABLE ir_model_fields (
  id serial,
  perm_id int references perm on delete set null,
  model varchar(64) DEFAULT ''::varchar NOT NULL,
  model_id int references ir_model on delete cascade,
  name varchar(64) DEFAULT ''::varchar NOT NULL,
  relation varchar(64),
  field_description varchar(256),
  ttype varchar(64),
  group_name varchar(64),
  view_load boolean,
  relate boolean default False,
  primary key(id)
);


-------------------------------------------------------------------------
-- Actions
-------------------------------------------------------------------------

CREATE TABLE ir_actions (
    id serial NOT NULL,
    perm_id int references perm on delete set null,
    name varchar(64) DEFAULT ''::varchar NOT NULL,
    "type" varchar(64) DEFAULT 'window'::varchar NOT NULL,
    usage varchar(32) DEFAULT null,
    primary key(id)
);

CREATE TABLE ir_act_window (
    view_id integer,
    res_model varchar(64),
    view_type varchar(16),
    "domain" varchar(127),
    primary key(id)
)
INHERITS (ir_actions);

CREATE TABLE ir_act_report_xml (
    model varchar(64) NOT NULL,
    report_name varchar(64) NOT NULL,
    report_xsl varchar(64),
    report_xml varchar(64),
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

CREATE TABLE ir_act_group (
    exec_type varchar(64) DEFAULT 'serial'::varchar NOT NULL,
    primary key(id)
)
INHERITS (ir_actions);

CREATE TABLE ir_act_group_link (
    aid integer NOT NULL,
    gid integer NOT NULL
);

CREATE TABLE ir_act_execute (
    func_name varchar(64) NOT NULL,
    func_arg varchar(64),
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

CREATE TABLE ir_ui_view (
	id serial NOT NULL,
	perm_id int references perm on delete set null,
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
	perm_id int references perm on delete set null,
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
    perm_id int references perm on delete set null,
    name varchar(64) not null,
    active boolean default True,
    login varchar(64) NOT NULL UNIQUE,
    password varchar(32) default null,
    perm_default int references perm on delete set null,
--  action_id int references ir_act_window on delete set null,
    action_id int,
    primary key(id)
);
alter table res_users add constraint res_users_login_uniq unique (login);

insert into res_users (id,login,password,name,action_id,perm_id,active) values (1,'root',NULL,'Root',NULL,1,False);
select setval('res_users_id_seq', 2);

CREATE TABLE res_groups (
    id serial NOT NULL,
    perm_id int references perm on delete set null,
    name varchar(32) NOT NULL,
    primary key(id)
);

create table res_roles (
    id serial NOT NULL,
    perm_id int references perm on delete set null,
    parent_id int references res_roles on delete set null,
    name varchar(32) NOT NULL,
    primary key(id)
);

CREATE TABLE res_roles_users_rel (
	uid integer NOT NULL references res_users on delete cascade,
	rid integer NOT NULL references res_roles on delete cascade
);

CREATE TABLE res_groups_users_rel (
	uid integer NOT NULL references res_users on delete cascade,
	gid integer NOT NULL references res_groups on delete cascade
);

---------------------------------
-- Workflows
---------------------------------

create table wkf
(
    id serial,
    perm_id int references perm on delete set null,
    name varchar(64),
    osv varchar(64),
    on_create bool default False,
    primary key(id)
);

create table wkf_activity
(
    id serial,
    perm_id int references perm on delete set null,
    wkf_id int references wkf on delete cascade,
    subflow_id int references wkf on delete set null,
    split_mode varchar(3) default 'XOR',
    join_mode varchar(3) default 'XOR',
    kind varchar(16) not null default 'dummy',
    name varchar(64),
    signal_send varchar(32) default null,
    flow_start boolean default False,
    flow_stop boolean default False,
    action varchar(64) default null,
    primary key(id)
);

create table wkf_transition
(
    id serial,
    perm_id int references perm on delete set null,
    act_from int references wkf_activity on delete cascade,
    act_to int references wkf_activity on delete cascade,
    condition varchar(128) default NULL,

    trigger_type varchar(128) default NULL,
    trigger_expr_id varchar(128) default NULL,

    signal varchar(64) default null,
    role_id int references res_roles on delete set null,

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
    perm_id integer,
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
    perm_id integer,
    create_uid integer references res_users on delete set null,
    create_date timestamp without time zone,
    write_date timestamp without time zone,
    write_uid integer references res_users on delete set null,
    website character varying(256),
    name character varying(128) NOT NULL,
    author character varying(128),
    url character varying(128),
    state character varying(16),
    latest_version character varying(64),
    shortdesc character varying(256),
    category_id integer REFERENCES ir_module_category ON DELETE SET NULL,
    description text,
    demo boolean default False,
    primary key(id)
);
ALTER TABLE ir_module_module add constraint name_uniq unique (name);

CREATE TABLE ir_module_module_dependency (
    id serial NOT NULL,
    perm_id integer,
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
    perm_id integer,
    name character varying(64) not null,
    parent_id integer references res_company on delete set null,
    primary key(id)
);

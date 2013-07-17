--
-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = off;
SET check_function_bodies = false;
SET client_min_messages = warning;
SET escape_string_warning = off;

SET search_path = public, pg_catalog;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: companies; Type: TABLE; Schema: public; Owner: fp; Tablespace: 
--

CREATE TABLE companies (
    id integer NOT NULL,
    company_name character varying
);


ALTER TABLE public.companies OWNER TO fp;

--
-- Name: companies_id_seq; Type: SEQUENCE; Schema: public; Owner: fp
--

CREATE SEQUENCE companies_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.companies_id_seq OWNER TO fp;

--
-- Name: companies_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: fp
--

ALTER SEQUENCE companies_id_seq OWNED BY companies.id;


--
-- Name: companies_id_seq; Type: SEQUENCE SET; Schema: public; Owner: fp
--

SELECT pg_catalog.setval('companies_id_seq', 3, true);


--
-- Name: persons; Type: TABLE; Schema: public; Owner: fp; Tablespace: 
--

CREATE TABLE persons (
    id integer NOT NULL,
    company_id integer,
    person_name character varying
);


ALTER TABLE public.persons OWNER TO fp;

--
-- Name: persons_id_seq; Type: SEQUENCE; Schema: public; Owner: fp
--

CREATE SEQUENCE persons_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.persons_id_seq OWNER TO fp;

--
-- Name: persons_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: fp
--

ALTER SEQUENCE persons_id_seq OWNED BY persons.id;


--
-- Name: persons_id_seq; Type: SEQUENCE SET; Schema: public; Owner: fp
--

SELECT pg_catalog.setval('persons_id_seq', 4, true);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: fp
--

ALTER TABLE ONLY companies ALTER COLUMN id SET DEFAULT nextval('companies_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: fp
--

ALTER TABLE ONLY persons ALTER COLUMN id SET DEFAULT nextval('persons_id_seq'::regclass);


--
-- Data for Name: companies; Type: TABLE DATA; Schema: public; Owner: fp
--

COPY companies (id, company_name) FROM stdin;
1	Bigees
2	Organi
3	Boum
\.


--
-- Data for Name: persons; Type: TABLE DATA; Schema: public; Owner: fp
--

COPY persons (id, company_id, person_name) FROM stdin;
1	1	Fabien
2	1	Laurence
3	2	Eric
4	3	Ramsy
\.


--
-- Name: companies_pkey; Type: CONSTRAINT; Schema: public; Owner: fp; Tablespace: 
--

ALTER TABLE ONLY companies
    ADD CONSTRAINT companies_pkey PRIMARY KEY (id);


--
-- Name: persons_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: fp
--

ALTER TABLE ONLY persons
    ADD CONSTRAINT persons_company_id_fkey FOREIGN KEY (company_id) REFERENCES companies(id);


--
-- PostgreSQL database dump complete
--


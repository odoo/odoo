# Module Dependency Analysis

## Top 30 Modules with Most Dependents

| Module | Dependents |
|---|---|
| [`account`](../addons/account) | 149 |
| [`base`](../../addons/base) | 44 |
| [`mail`](../addons/mail) | 43 |
| [`account_edi_ubl_cii`](../addons/account_edi_ubl_cii) | 42 |
| [`base_vat`](../addons/base_vat) | 40 |
| [`web`](../addons/web) | 37 |
| [`point_of_sale`](../addons/point_of_sale) | 36 |
| [`base_iban`](../addons/base_iban) | 25 |
| [`payment`](../addons/payment) | 21 |
| [`sale`](../addons/sale) | 21 |
| [`website`](../addons/website) | 20 |
| [`base_setup`](../addons/base_setup) | 19 |
| [`hr`](../addons/hr) | 18 |
| [`portal`](../addons/portal) | 17 |
| [`sms`](../addons/sms) | 17 |
| [`l10n_syscohada`](../addons/l10n_syscohada) | 17 |
| [`website_sale`](../addons/website_sale) | 16 |
| [`crm`](../addons/crm) | 15 |
| [`digest`](../addons/digest) | 13 |
| [`spreadsheet_dashboard`](../addons/spreadsheet_dashboard) | 13 |
| [`mass_mailing`](../addons/mass_mailing) | 13 |
| [`stock`](../addons/stock) | 11 |
| [`web_tour`](../addons/web_tour) | 10 |
| [`stock_account`](../addons/stock_account) | 10 |
| [`sale_stock`](../addons/sale_stock) | 10 |
| [`mrp`](../addons/mrp) | 10 |
| [`resource`](../addons/resource) | 9 |
| [`calendar`](../addons/calendar) | 9 |
| [`event`](../addons/event) | 9 |
| [`sale_management`](../addons/sale_management) | 9 |

## Likely Base Layers
Modules with many dependents but few dependencies (<= 3).

| Module | Dependents | Dependencies |
|---|---|---|
| [`base`](../../addons/base) | 44 | None |
| [`account_edi_ubl_cii`](../addons/account_edi_ubl_cii) | 42 | [`account`](../addons/account) |
| [`base_vat`](../addons/base_vat) | 40 | [`account`](../addons/account) |
| [`web`](../addons/web) | 37 | [`base`](../../addons/base) |
| [`base_iban`](../addons/base_iban) | 25 | [`account`](../addons/account), [`web`](../addons/web) |
| [`payment`](../addons/payment) | 21 | [`onboarding`](../addons/onboarding), [`portal`](../addons/portal) |
| [`sale`](../addons/sale) | 21 | [`sales_team`](../addons/sales_team), [`account_payment`](../addons/account_payment), [`utm`](../addons/utm) |
| [`base_setup`](../addons/base_setup) | 19 | [`base`](../../addons/base), [`web`](../addons/web) |
| [`l10n_syscohada`](../addons/l10n_syscohada) | 17 | [`account`](../addons/account) |
| [`digest`](../addons/digest) | 13 | [`mail`](../addons/mail), [`portal`](../addons/portal), [`resource`](../addons/resource) |
| [`spreadsheet_dashboard`](../addons/spreadsheet_dashboard) | 13 | [`spreadsheet`](../addons/spreadsheet) |
| [`stock`](../addons/stock) | 11 | [`product`](../addons/product), [`barcodes_gs1_nomenclature`](../addons/barcodes_gs1_nomenclature), [`digest`](../addons/digest) |
| [`web_tour`](../addons/web_tour) | 10 | [`web`](../addons/web) |
| [`stock_account`](../addons/stock_account) | 10 | [`stock`](../addons/stock), [`account`](../addons/account) |
| [`sale_stock`](../addons/sale_stock) | 10 | [`sale`](../addons/sale), [`stock_account`](../addons/stock_account) |
| [`mrp`](../addons/mrp) | 10 | [`product`](../addons/product), [`stock`](../addons/stock), [`resource`](../addons/resource) |
| [`resource`](../addons/resource) | 9 | [`base`](../../addons/base), [`web`](../addons/web) |
| [`calendar`](../addons/calendar) | 9 | [`base`](../../addons/base), [`mail`](../addons/mail) |
| [`sale_management`](../addons/sale_management) | 9 | [`sale`](../addons/sale), [`digest`](../addons/digest) |
| [`utm`](../addons/utm) | 8 | [`base`](../../addons/base), [`web`](../addons/web) |
| [`hr_holidays`](../addons/hr_holidays) | 8 | [`hr`](../addons/hr), [`calendar`](../addons/calendar), [`resource`](../addons/resource) |
| [`html_editor`](../addons/html_editor) | 8 | [`base`](../../addons/base), [`bus`](../addons/bus), [`web`](../addons/web) |
| [`l10n_gcc_invoice`](../addons/l10n_gcc_invoice) | 8 | [`account`](../addons/account) |
| [`l10n_din5008`](../addons/l10n_din5008) | 8 | [`account`](../addons/account) |
| [`account_debit_note`](../addons/account_debit_note) | 8 | [`account`](../addons/account) |
| [`contacts`](../addons/contacts) | 7 | [`base`](../../addons/base), [`mail`](../addons/mail) |
| [`iap_mail`](../addons/iap_mail) | 7 | [`iap`](../addons/iap), [`mail`](../addons/mail) |
| [`l10n_latam_base`](../addons/l10n_latam_base) | 7 | [`contacts`](../addons/contacts), [`base_vat`](../addons/base_vat) |
| [`pos_restaurant`](../addons/pos_restaurant) | 7 | [`point_of_sale`](../addons/point_of_sale) |
| [`purchase`](../addons/purchase) | 7 | [`account`](../addons/account) |
| [`purchase_stock`](../addons/purchase_stock) | 7 | [`stock_account`](../addons/stock_account), [`purchase`](../addons/purchase) |
| [`mass_mailing_sms`](../addons/mass_mailing_sms) | 7 | [`portal`](../addons/portal), [`mass_mailing`](../addons/mass_mailing), [`sms`](../addons/sms) |
| [`pos_self_order`](../addons/pos_self_order) | 7 | [`pos_restaurant`](../addons/pos_restaurant), [`http_routing`](../addons/http_routing), [`link_tracker`](../addons/link_tracker) |
| [`auth_signup`](../addons/auth_signup) | 6 | [`base_setup`](../addons/base_setup), [`mail`](../addons/mail), [`web`](../addons/web) |
| [`phone_validation`](../addons/phone_validation) | 6 | [`base`](../../addons/base), [`mail`](../addons/mail) |
| [`event_sale`](../addons/event_sale) | 6 | [`event_product`](../addons/event_product), [`sale_management`](../addons/sale_management) |

## Core Dependency Backbone (Mermaid)

```mermaid
%%{ init: { 'flowchart': { 'curve': 'step', 'nodeSpacing': 100, 'rankSpacing': 150 } } }%%
graph LR;
    classDef base fill:#f5f5f5,stroke:#616161,stroke-width:2px,color:#333,padding:20px;
    classDef web fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#333,padding:20px;
    classDef account fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#333,padding:20px;
    classDef sale fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,color:#333,padding:20px;
    classDef stock fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#333,padding:20px;
    classDef mrp fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#333,padding:20px;
    classDef hr fill:#e0f7fa,stroke:#00838f,stroke-width:2px,color:#333,padding:20px;
    classDef pos fill:#fffde7,stroke:#fbc02d,stroke-width:2px,color:#333,padding:20px;
    classDef marketing fill:#fce4ec,stroke:#c2185b,stroke-width:2px,color:#333,padding:20px;
    classDef l10n fill:#e8eaf6,stroke:#3949ab,stroke-width:2px,color:#333,padding:20px;
    classDef productivity fill:#f9fbe7,stroke:#827717,stroke-width:2px,color:#333,padding:20px;
    classDef other fill:#ffffff,stroke:#9e9e9e,stroke-width:1px,stroke-dasharray: 5 5,color:#333,padding:20px;
    subgraph cluster_base ["BASE"]
        base_vat
        base_setup
        base_iban
        base
    end
    class base_vat,base_setup,base_iban,base base;
    subgraph cluster_web ["WEB"]
        portal
        website_sale
        web
        web_tour
    end
    class portal,website_sale,web,web_tour web;
    subgraph cluster_account ["ACCOUNT"]
        account
        payment
        account_edi_ubl_cii
    end
    class account,payment,account_edi_ubl_cii account;
    subgraph cluster_sale ["SALE"]
        sale
        sale_stock
        sale_management
    end
    class sale,sale_stock,sale_management sale;
    subgraph cluster_stock ["STOCK"]
        stock
        stock_account
    end
    class stock,stock_account stock;
    subgraph cluster_mrp ["MRP"]
        mrp
    end
    class mrp mrp;
    subgraph cluster_hr ["HR"]
        hr
    end
    class hr hr;
    subgraph cluster_apps ["MISC APPS"]
        direction TB
        subgraph cluster_pos ["POS"]
            point_of_sale
        end
        class point_of_sale pos;
        subgraph cluster_marketing ["MARKETING"]
            mass_mailing
            crm
            sms
        end
        class mass_mailing,crm,sms marketing;
        subgraph cluster_l10n ["L10N"]
            l10n_syscohada
        end
        class l10n_syscohada l10n;
        subgraph cluster_productivity ["PRODUCTIVITY"]
            resource
            event
            calendar
            digest
            spreadsheet_dashboard
        end
        class resource,event,calendar,digest,spreadsheet_dashboard productivity;
        subgraph cluster_other ["OTHER"]
            website
            mail
        end
        class website,mail other;
    end
    resource --> base;
    resource --> web;
    sale_stock --> sale;
    sale_stock --> stock_account;
    portal --> web;
    portal --> mail;
    stock --> digest;
    base_vat --> account;
    sale_management --> sale;
    sale_management --> digest;
    base_setup --> base;
    base_setup --> web;
    event --> base_setup;
    event --> mail;
    event --> portal;
    calendar --> base;
    calendar --> mail;
    hr --> base_setup;
    hr --> digest;
    hr --> web;
    website_sale --> website;
    website_sale --> sale;
    website_sale --> digest;
    base_iban --> account;
    base_iban --> web;
    web --> base;
    account --> base_setup;
    account --> portal;
    account --> digest;
    web_tour --> web;
    l10n_syscohada --> account;
    point_of_sale --> resource;
    point_of_sale --> stock_account;
    point_of_sale --> digest;
    payment --> portal;
    digest --> mail;
    digest --> portal;
    digest --> resource;
    mrp --> stock;
    mrp --> resource;
    website --> digest;
    website --> web;
    website --> portal;
    website --> mail;
    account_edi_ubl_cii --> account;
    mass_mailing --> mail;
    mass_mailing --> web_tour;
    mass_mailing --> digest;
    crm --> base_setup;
    crm --> mail;
    crm --> calendar;
    crm --> resource;
    crm --> web_tour;
    crm --> digest;
    sms --> base;
    sms --> mail;
    mail --> base;
    mail --> base_setup;
    mail --> web_tour;
    stock_account --> stock;
    stock_account --> account;
    linkStyle 0,1,12,13,14,15,16,35,36,37 stroke:#827717,stroke-width:2px;
    linkStyle 2,3,8,9 stroke:#ef6c00,stroke-width:2px;
    linkStyle 4,5,20,21,22,25,29 stroke:#1565c0,stroke-width:2px;
    linkStyle 6,59,60 stroke:#7b1fa2,stroke-width:2px;
    linkStyle 7,10,11,23,24 stroke:#616161,stroke-width:2px;
    linkStyle 17,18,19 stroke:#00838f,stroke-width:2px;
    linkStyle 26,27,28,34,44 stroke:#2e7d32,stroke-width:2px;
    linkStyle 30 stroke:#3949ab,stroke-width:2px;
    linkStyle 31,32,33 stroke:#fbc02d,stroke-width:2px;
    linkStyle 38,39 stroke:#c62828,stroke-width:2px;
    linkStyle 40,41,42,43,56,57,58 stroke:#9e9e9e,stroke-width:2px;
    linkStyle 45,46,47,48,49,50,51,52,53,54,55 stroke:#c2185b,stroke-width:2px;

    click sale "../addons/sale" "Open sale module";
    click resource "../addons/resource" "Open resource module";
    click sale_stock "../addons/sale_stock" "Open sale_stock module";
    click portal "../addons/portal" "Open portal module";
    click stock "../addons/stock" "Open stock module";
    click base_vat "../addons/base_vat" "Open base_vat module";
    click sale_management "../addons/sale_management" "Open sale_management module";
    click base_setup "../addons/base_setup" "Open base_setup module";
    click event "../addons/event" "Open event module";
    click calendar "../addons/calendar" "Open calendar module";
    click hr "../addons/hr" "Open hr module";
    click website_sale "../addons/website_sale" "Open website_sale module";
    click base_iban "../addons/base_iban" "Open base_iban module";
    click account "../addons/account" "Open account module";
    click web "../addons/web" "Open web module";
    click web_tour "../addons/web_tour" "Open web_tour module";
    click l10n_syscohada "../addons/l10n_syscohada" "Open l10n_syscohada module";
    click point_of_sale "../addons/point_of_sale" "Open point_of_sale module";
    click payment "../addons/payment" "Open payment module";
    click digest "../addons/digest" "Open digest module";
    click mrp "../addons/mrp" "Open mrp module";
    click website "../addons/website" "Open website module";
    click base "../../addons/base" "Open base module";
    click account_edi_ubl_cii "../addons/account_edi_ubl_cii" "Open account_edi_ubl_cii module";
    click mass_mailing "../addons/mass_mailing" "Open mass_mailing module";
    click crm "../addons/crm" "Open crm module";
    click stock_account "../addons/stock_account" "Open stock_account module";
    click mail "../addons/mail" "Open mail module";
    click sms "../addons/sms" "Open sms module";
    click spreadsheet_dashboard "../addons/spreadsheet_dashboard" "Open spreadsheet_dashboard module";
```

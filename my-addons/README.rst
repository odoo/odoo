Deltatech
==========

.. |badge1| image:: https://img.shields.io/badge/license-LGPL--3-blue.png
    :target: http://www.gnu.org/licenses/lgpl-3.0-standalone.html
    :alt: License: LGPL-3

.. |badge2| image:: https://img.shields.io/badge/github-dhongu%2Fdeltatech-lightgray.png?logo=github
    :target: https://github.com/dhongu/deltatech
    :alt: dhongu/deltatech

.. |badge3| image:: https://travis-ci.org/dhongu/deltatech.svg?branch=14.0
    :target: https://travis-ci.org/dhongu/deltatech
    :alt: build

.. |badge4| image:: https://codecov.io/gh/dhongu/deltatech/branch/14.0/graph/badge.svg
    :target: https://codecov.io/gh/dhongu/deltatech
    :alt: codecov


|badge1| |badge2| |badge3| |badge4|


deltatech
---------

It's a generic module, it does not do anything special.


deltatech_alternative
---------------------

.. include:: deltatech_alternative/DESCRIPTION.rst

deltatech_account
--------------------------------
- permite dezactivarea de jurnale
- adauga grupul pentru butoane din dreapta sus in facturi



deltatech_account_followup
--------------------------------
- permite blocarea partenerului, cu mesaj de blocare



deltatech_alternative
--------------------------------
- permite definirea unui catalog de produse pentru un numar foarte mare de produse care uzual nu se folosesc
- la cautarea dupa un cod din catalog, sistemul genereaza automat un produs (product.product), copie dupa cel din catalog
- se defineste modelul product_alternative
- se poate cauta un produs dupa alternativa
- in product.template sunt definite campurile:
	- alternative_code - concatenarea tuturor codurilor alternative
	- alternative_ids - lista de produse alternative
	- used_for - la ce este utilizat produsul (text)



deltatech_alternative_inv
--------------------------------
- afiseaza codurile alternative in factura



deltatech_alternative_website
--------------------------------
- cautare produs dupa cod echivalent in website
- afisare imagini produse in magazinul virtual cu watermark
- adauga categoriile afisate in website la catalogul de produse



deltatech_bank_statement
--------------------------------
- adauga in liniile extrasului de banca, la referinta, numarul facturii care a fost reconciliata



deltatech_cash_statement
--------------------------------
- actualizare automata a soldurilor de inceput si sfarsit la registru de casa (wizard)



deltatech_config_vat
--------------------------------
- la modificarea TVA-ului implicit, se modifica TVA-urile la toate produsele si la toate comenzile deschise
- se recomanda dezinstalarea modulului dupa schimbarea TVA-ului



deltatech_contact
--------------------------------
- adaugare campuri suplimentare in datele de contact: data nasterii, CNP, carte de identitate, mijloc de transport, daca este departament
- este redefinita metoda de afisare a numelui partenerului, cu posibilitatea de trimitere in context a parametrilor:
	- show_address_only - pentru afisare doar a adresei
	- show_address - afiseaza si adresa
	- show_email - afiseaza e-mail-ul
	- show_phone - afiseaza telefonul
	- show_category - afiseaza etichetele
- cautare directa partener dupa VAT



deltatech_credit_limit
--------------------------------
- posibilitate de verificare a limitei de credit la confirmarea comenzii de vanzare



deltatech_crm
--------------------------------
- preluare functionalitati de activitati din Odoo 9, inclusiv report-urile
- la creearea unui lead din mail, se preiau campurile din tag-urile speciale
- buton in oportunitate pentru afisarea comenzii de vanzare/ofreta asociate
- asignare template de mail la etapa unei oportunitati
- wizard pentru modoficarea in masa a agentului de vanzari la oportunitati



deltatech_crm_claim_8D
--------------------------------
- implementeaza sistemul de gestionare a problemelor "8D"
- poate functiona cu modulul CRM standard sau, daca nu este nevoie, se poate instala modulul deltatech_simple_crm (se face modificarea in __openerp__.py)



deltatech_crm_doc
--------------------------------
- gestionare documente legate de oportunitati



deltatech_crm_survey
--------------------------------
- adugarea de chestionar la un stadiu a oportunitatii/lead
- adugarea de chestionar la eticheta oportunitatii/lead
- adugare rezultate chestionar la oportunitate



deltatech_datecs_print
--------------------------------
- generare bon fiscal din factura pentru casa de marcat DATECS



deltatech_document
--------------------------------
- nr document automat dat de sistem, din categoria documentului
- campuri noi:
	- Description
	- Turtle reference
	- tipuri document Procedure, Template, Work Instruction
	- Departament
	- Reasons
	- Issued by: automat numele celui care creaza doc, numai administratorul poate avea acces de editare (asta daca vrea sa emite un doc in numele altei persoane)
	- Inform: in acest camp sa se poata selecta mai multi utilizatori care vor fi informati de noul document, revizie sau alte modificari.
	- Approved by : sa se poat selecta cel putin 1 utilizator care trebuie sa aprobe
- Documentul se inregistreaza in arhiva numai dupa ce a fost aprobat
- Documentele in stand by le pot vedea doar emitentii si cei care trebuie sa-l aprobe



deltatech_expenses
==================
- gestionarea decontului de cheltuieli
- Introducerea decontului de cheltuieli intr-un document distict ce genereaza automat chitante de achizitie
- Validarea documentului duce la generarea notelor contabile de avans si inegistrarea platilor
- permite tiparirea decontului



deltatech_fast_sale
--------------------------------
- buton in comanda de vanzare pentru a face pasii de confirmare, livrare si facturare



deltatech_gamification
--------------------------------
- permite stabilirea unei tinte cu valoare negativa



deltatech_hr_attendance
--------------------------------
- adaugare camp de data pentru raportarea prezentei



deltatech_invoice
--------------------------------
- calcul pret produs in functie de lista de preturi aferenta clientului/furnizorului
- validare data factura sa fie mai mare decat data din ultima factura
- nr. factura editabil
- permite 2 formulare pentru tiparirea facturii
- va fi revizuit


deltatech_invoice_number
--------------------------------
- wizard pentru modificarea numarului de factura



deltatech_invoice_product_filter
================================
- permite cautarea facturii dupa produs



deltatech_invoice_receipt
--------------------------------
 - Adaugare buton nou in factura de receptie care  genereaza document de receptie stocuri
 - Nu se permite achizitia unui produs stocabil fara comanda aprovizionare (picking in asteptare).
 - La creare factura din picking se face ajustarea automata a monedei de facturare in conformitate cu moneda din jurnal
 - Adaugat buton pentru a genera un picking in asteptare in conformitate cu liniile din factura
 - Se permite generarea unei document de receptie pentru produsele care nu au comanda de achizitie
 - Pretul produselor se actualizeaza automat pentru receptiile fara comanda de achizitie
 - Furnizorul produselor se actualizeaza automat pentru receptiile fara comanda de achizitie
 - Calcul pret produs in functie de lista de preturi aferenta clientului/furnizorului
 - buton in factura pentru afisarea stocului pentru produsele din factura
Antentie:
 - la inregistrarea facturilor in care sunt un produs apare de mai multe ori cu preturi diferite! Ia doar unul!



deltatech_invoice_report
--------------------------------
- Adaugare in raportul de analiza facturi a campurilor: judet, nr de factura si furnizor



deltatech_invoice_residual
--------------------------------
- Calcul Sold factura in cazul in care totalul de pe facura este negativ, standard facturile nu au sold negativ



deltatech_invoice_weight
--------------------------------
- permite afisarea maselor (net, brut, pachet) in factura



deltatech_mail
--------------
 - Trimite email orice document din sistem
 - parternerii sunt automat adaugati la urmaritori dupa trimiterea e-mail-ului daca se selecteaz acest lucru
 - Setare documente ca citite
 - Setare documente ca necitite
 - Se permite trimiterea de email doar la persoanele selectate
 - Notificare la primire mesaj
 - posibilitate de a bloca trimiterea de mail-uri in afara sistemului
 - Deschiderea unui document nu il marcheaza ca citit
 - la compunera unui email  sistemul ataseaza automat toate atasamentele documentului. Se pot elimina manual
 - Marcheaza cu culoarea rosie mesajele primite din afara sistemului in istoricul documentului



deltatech_mail_automatically
----------------------------
 - Se permite trimiterea automata de e-mail-uri la o lista de persoane configurabila, la validarea unei facturi si la validarea unui transfer



deltatech_mentor
----------------
 - Permite exportul de facturi si parteneri pentru WinMentor



deltatech_mrp_bom_cost
----------------------
 - Permite calculul automat al pretului BOM-ului
 - Permite definirea unui cost indirect procentual
 - Grupeaza miscarile de stoc pentru o comanda de productie intr-un picking



deltatech_mrp_cost
------------------
 - Calculeaza automat pretul de productie ca fiind pretul real al componentelor
 - Simplifica lista de materiale



deltatech_mrp_edit_comp
-----------------------
 - Permite modificarea in comanda de productie a listei de materiale



deltatech_mrp_operations
------------------------
 - Permite alocarea de operatori la centrele de lucru
 - Confirmarea comenzilor de productie prin scanarea de coduri de bare.
        Se inreagistreaza activitatile pe operatori



deltatech_mrp_sale
------------------
 - Se permite intocmirea unei liste de produse in comanda de vanzare
 - In lista de produse se pot defini atribute
 - se face explozia listei initiale in a lista de componente
 - se calculeaza pretul si marginea

 - se permite ca in lista de materiale sa existe cantitati negative (recuperari)

 - se permite editarea manuala a atibutelor unui produs
 - se pot defini valori implicite la atribute - preluate in comanda de vanzare

 - se permite adaugarea unei margini pe fiecare pozitie
 - se va muta in alt repo



deltatech_parallel_valuation
----------------------------
 - Definire moneda paralela de evaluare si raportare
 - Evaluarea  stocului in moneda paralela
 - Afisare curs valutar in moneda paralela
 - Raport de stoc valorinc exprimat in moneda paralela la data curenta
 - Camp pentru curs valutar in factura
 - Data facturii  editabila si in cazul in care factura este in starea proforma
 - Nume/referinta factura  editabil si in cazul in care factura este in starea proforma
 - In raportul standard de analiza facturi au foat adaugate doua colone cu valoarea stocului in moneda paralela si cu valoarea liniei in moneda paralela
 - Pretul de cost este afisat doar la manager depozit



deltatech_payment_term
----------------------
 - Permite generarea de termene de plata din comanda de vanzare, pentru vanzarea in rate
 - Afisarea in rapoarte daca comanda de vanzare/factura este in rate



deltatech_percent_qty
---------------------
 - Introduce unitatea de masura %
 - Daca in comanda de vanzare se utilizeaza un produs care are unitatea de masura procent atunci pretul este calculat prin suma valorilor liniilor din comanda filtrate cu ajutorul domeniului definit la produs
 - Camp nou in produs in care se poate specifica un domeniul pentru care se calculeaza pretul
 - Actualizarea pretului se face manual (buton)



deltatech_picking_number
------------------------
 - Numerotare liste de ridicare la cerere
 - Gama de numere se configureaza pentru fiecare tip de operatie



deltatech_price_categ
---------------------
 - Adaugare a 3 campuri in produs pentru 3 categorii de pret: bronze, silver, gold



deltatech_pricelist
-------------------
 - Acces din meniu la pozitii din listele de preturi
 - Camp nou pt afisare text calcul pret
 - Camp nou pt cod lista de preturi



deltatech_procurement
---------------------
 - Afisare procent de facturare in comanda de vanzare/achizitie
 - Buton in comanda de vanzare/achizitie pentru afisare comanda de aprovizionare (necesarului de stoc)
 - Posibilitate de introducere de catre utilizatori a unei cereri de achizitie, care dupa aprobarea lor creeaza comenzi de aprovizionare
 - Trecerea de la make_to_order la make_to_stock in cazul transferurilor interne
 - Afisare campuri de cantitate disponibila in comanda de vanzare
 - Daca produsul se cumpara atunci trebuie definit obligatoriu un furnizor
 - Pozitiile din lista de ridicare sunt editabile
 - Afisare locatie sursa in lista cu pozitiile din lista de ridicare
 - Filtru my pentru liste de ridicare
 - Adugare buton in comanda de vanzare,comanda de achzitie si lista de ridicare pentru consultare pozitii de stoc cu produsele din document
 - Butonul Scrap Products este afisat doar la manager stoc
 - Anularea in masa a aprovizionarilor
 - Buton nou in lista de ridicare pentru validare (de catre alt utilizator, daca e necesar) operare transfer fizic
 - Camap nou in comanda de vanzare pentru specificare date de livrare, date care sunt preluate in picking



deltatech_product_code
----------------------
 - Generare automata cod intern la produse



deltatech_product_extension
---------------------------
 - Adaugare campuri in produs: dimensiuni, durata de viata si unitate de masura pt. durata de viata



deltatech_project
-----------------
 - Se poate aloca in cadrul unui task o pondere a acestuia in cadrul proiectului
 - Progresul unui proiect este calculat automat in functie de ponderile task-urilor si recursiv in functie de progresul subproiectelor
 - Posibilitate de definire de task-uri recurente
 - Posibilitatea de adaugare atasamente la proiect/task
 - Rapoarte cu task-urile pentru azi, maine, alta data



deltatech_purchase_xls
----------------------
 - Export comanda de achizitie in format Excel



deltatech_qr_invoice
--------------------
 - Adaugare cod QR pe factura



deltatech_quant
---------------
 - Afisare coloana de categorie produs in lista de pozitii de stoc
 - Adaugare client pentru pozitiile de stoc livrate care un partener
 - Adaugare furnizor pentru pozitiile de stoc achizitionate
 - Coloana cu numarul facturii de achiztiei
 - Ofera posibilitatea de a modifica lotul unei pozitii de stoc
 - Permite impartirea unei pozitii de stoc



deltatech_quant_purchase_unit
-----------------------------
 - afisarea in pozitiile de stoc si a cantitatii in unitatea de masura de aprovizionare



deltatech_rec_access
--------------------
 - Restrictionare acces la transfer stoc
 - Restrictionare acces la confirmare comanda de vanzare
 - Afisare stoc personal (dezactivat)
 - Afisare miscari personale (dezactivat)
 - Afisare quanturi proprii (dezactivat)



deltatech_refund
----------------
 - Adaugare de campuri in factura pentru a face legatura dintre factura stornata si factura initiala
 - Adaugare de campuri in picking pentru a face legatura dintre picking-ul stornat/rambursat si picking-ul initial
 - La anularea unei facturi se va vor anula in mod automat si miscarile de stoc aferente, in functie de configurare (companie). Anularea se face prin apasarea unui buton
 - La o rambursare se poate genera un nou picking in asteptare
 - Documentul de rambursare se poate transfera in mod automat
 - La stergerea unei facturi se va schimba si starea picking listului (in de facturat)
 - In lista de ridicari sunt afisate rambursarile cu gri si italic

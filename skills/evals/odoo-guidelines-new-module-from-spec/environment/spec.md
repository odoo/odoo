# Print shipping labels on network printers

## Why

Warehouses print carrier labels and export documents on label printers. Today
that needs an IoT box between Odoo and the printer. Many warehouses only have
network printers, Zebra label printers and Epson thermal printers, sitting on
the same network as the packing station's computer. We want Odoo to send
documents straight to those printers from the browser, without an IoT box, and
to print the carrier labels of a delivery automatically when it is validated.

Printing to a network printer must be available to any report, not only to
shipping labels: product labels, delivery slips, and so on. Other modules (the
IoT box support, in particular) must be able to add more kinds of printers
later.

## Who

- Warehouse workers print, and pick the printers they use from their own
  computer.
- Any internal user can register printers and edit them; inventory managers
  can also delete them.

## Printers

A printer has:

- a name;
- its address on the network: an IP address or a host name, optionally with a
  port or a path (`192.168.1.20`, `zebra-1.local:8080`);
- its kind: *ZPL* (Zebra label printers) or *ePOS* (Epson thermal printers),
  ZPL by default;
- the reports it prints.

The link between printers and reports can be edited from both sides: on the
printer, and on the report's form (Settings, technical reports), where the
report gets a "Printers" field next to its paper format.

Printers are managed from Inventory: Configuration > Reporting > Manage
Printers. Where the kind of a printer matters to tell two printers apart (in a
selection dialog, for example), it is shown with the name ("ZPL - Packing
station").

## Printing a report to printers

When a user prints a report that has printers, from any print menu or
automatically, the document goes to the printers instead of being downloaded:

1. The first time a user prints that report in a browser, a dialog asks which
   of the report's printers to use, with a "Do not ask me again" option. At
   least one printer must be chosen ("Select at least one printer"). The
   choice is remembered in that browser, per report.
2. Next times, if "Do not ask me again" was checked, the document goes to the
   remembered printers without asking. Otherwise the dialog opens again with
   the remembered printers already selected.
3. Closing the dialog without choosing prints the report the usual way (a
   download).
4. Each printer receives the documents of its own kind: a ZPL printer gets the
   ZPL output, an ePOS printer gets the image. Documents are sent one after
   the other.
5. When a printer reports an error, the user gets a notification saying the
   document could not be printed, with the printer's error code, and printing
   goes on with the next document. When an ePOS printer answers that it is
   waiting for the previous label to be taken out (`ERROR_WAIT_EJECT`), the
   same document is sent again a second later instead.
6. A user can forget the remembered choices: a "Reset Linked Printers" page,
   in the same Configuration > Reporting menu and available to every
   inventory user (even those who do not see the rest of the Configuration
   menu), lists the reports with remembered printers in that browser, each
   with a button to forget its choice.

What the printers receive:

- **ZPL printers** print the reports whose output is ZPL text: a text report
  with "ZPL" in its name (Odoo's ZPL product labels, for example). The text is
  sent as is.
- **ePOS printers** print PDF reports, turned into an image the printer can
  print: rendered as a picture of the page, in portrait (a landscape page is
  turned), 576 dots wide (the paper width), in black and white with
  dithering. Relative links in the report (barcode images, for example) must
  still resolve when the report is rendered for the printer.

## Shipping labels and export documents

When a delivery is validated, the carriers that create labels (DHL, FedEx,
UPS, ...) save them in the delivery's chatter, as attachments named
`Label...`, and their export documents as attachments named `ShippingDoc...`.

- Two new printable reports on transfers, **Shipping Labels** and **Shipping
  Documents**, print those attachments, the most recent first: to ZPL
  printers, the `.zpl` attachments; to ePOS printers, the image attachments
  (`.png`, `.jpg`, `.jpeg`), turned into the printer's format as above.
- They are meant for printers. Printed the usual way, as a download (when the
  user closes the printer dialog, for example), they download the most recent
  attachment when it is a PDF, and otherwise explain what is wrong: there is
  no such attachment in the chatter; or the report has no printer configured;
  or the attachment is not a PDF (configure the carrier to produce PDF, or use
  a ZPL or ePOS printer).
- Operation types (outgoing and internal ones) get two options, **Carrier
  Labels** and **Export Documents**, to print them automatically when a
  transfer of that type is validated, next to the existing automatic printing
  options. A notice next to them explains that the documents are saved in the
  chatter at validation and need a printer set on the report to be printed
  automatically, with a link to each report's form, where the printer is then
  required.

## Demo data

Two demo printers, an emulated Zebra and an emulated ePOS, and the demo Zebra
printer prints the ZPL product labels.

## Printer interfaces

What the printers expect, from their manufacturers' documentation. The browser
talks to them directly: the printers are on the local network, the Odoo server
usually is not.

**Zebra (ZPL).** Send the ZPL text in an HTTP `POST` to
`http://<address>/pstprnt`, as `text/plain; charset=utf-8`. The printer's web
server does not answer CORS preflight requests, so the request must be sent in
`no-cors` mode, and its result cannot be read: a request that went through
counts as printed.

**Epson (ePOS-Print).** Send an HTTP `POST` to
`http://<address>/cgi-bin/epos/service.cgi?devid=local_printer` with a SOAP
envelope:

```xml
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
    <s:Body>
        <epos-print xmlns="http://www.epson-pos.com/schemas/2011/03/epos-print">
            <image width="576" height="HEIGHT" align="center">RASTER</image>
            <cut type="feed" />
        </epos-print>
    </s:Body>
</s:Envelope>
```

`RASTER` is the base64 of the 1-bit image, row by row from the top, 8 dots per
byte, a set bit printing black; `HEIGHT` is its number of rows. The printer
answers with an XML document holding a `<response success="true|false"
code="...">` element. Give up on a printer that does not answer within 15
seconds.

## Out of scope

- Printing through an IoT box (another module does it).
- Duplex printing and other printer settings.
- Other kinds of printers.

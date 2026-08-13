{
  "version": "19.3.10",
  "sheets": [
    {
      "id": "dashboard_sheet_id",
      "name": "Dashboard",
      "colNumber": 10,
      "rowNumber": 43,
      "rows": {
        "42": { "size": 3 }
      },
      "cols": {
        "0": { "size": 136 }
      },
      "merges": [],
      "cells": {},
      "styles": {},
      "formats": {},
      "borders": {},
      "conditionalFormats": [],
      "dataValidationRules": [],
      "figures": [
        {
          "id": "a761d77e-17d1-4d7a-ac85-5494c07dd360",
          "width": 209,
          "height": 106,
          "tag": "chart",
          "data": {
            "baselineColorDown": "#DC6965",
            "baselineColorUp": "#00A04A",
            "baselineMode": "percentage",
            "title": { "text": "Carts", "bold": true, "color": "#017E84" },
            "type": "scorecard",
            "background": "",
            "baseline": "Data!E2",
            "baselineDescr": { "text": "since last period" },
            "keyValue": "Data!D2",
            "humanize": false,
            "chartId": "a761d77e-17d1-4d7a-ac85-5494c07dd360"
          },
          "offset": { "x": 0, "y": 9 },
          "col": 0,
          "row": 0
        },
        {
          "id": "7db1cb48-a155-4984-b8dd-de155db2b65f",
          "width": 209,
          "height": 106,
          "tag": "chart",
          "data": {
            "baselineColorDown": "#DC6965",
            "baselineColorUp": "#00A04A",
            "baselineMode": "percentage",
            "title": { "text": "Orders", "bold": true, "color": "#017E84" },
            "type": "scorecard",
            "background": "",
            "baseline": "Data!E3",
            "baselineDescr": { "text": "since last period" },
            "keyValue": "Data!D3",
            "humanize": false,
            "chartId": "7db1cb48-a155-4984-b8dd-de155db2b65f"
          },
          "offset": { "x": 219, "y": 9 },
          "col": 0,
          "row": 0
        },
        {
          "id": "1bfef494-7090-4263-8e07-83f14f43c0e7",
          "width": 209,
          "height": 106,
          "tag": "chart",
          "data": {
            "baselineColorDown": "#DC6965",
            "baselineColorUp": "#00A04A",
            "baselineMode": "percentage",
            "title": { "text": "Abandoned Carts", "bold": true, "color": "#017E84" },
            "type": "scorecard",
            "background": "",
            "baseline": "Data!E4",
            "baselineDescr": { "text": "since last period" },
            "keyValue": "Data!D4",
            "humanize": false,
            "chartId": "1bfef494-7090-4263-8e07-83f14f43c0e7"
          },
          "offset": { "x": 438, "y": 9 },
          "col": 0,
          "row": 0
        },
        {
          "id": "79d91c01-7aeb-4845-aa82-5a41895b74af",
          "width": 209,
          "height": 106,
          "tag": "chart",
          "data": {
            "baselineColorDown": "#DC6965",
            "baselineColorUp": "#00A04A",
            "baselineMode": "percentage",
            "title": { "text": "Total Revenue", "bold": true, "color": "#017E84" },
            "type": "scorecard",
            "background": "",
            "baseline": "Data!E5",
            "baselineDescr": { "text": "since last period" },
            "keyValue": "Data!D5",
            "humanize": false,
            "chartId": "79d91c01-7aeb-4845-aa82-5a41895b74af"
          },
          "offset": { "x": 657, "y": 9 },
          "col": 0,
          "row": 0
        },
        {
          "id": "05f3bc5f-1628",
          "col": 0,
          "row": 0,
          "offset": { "x": 505, "y": 542 },
          "width": 495,
          "height": 407,
          "tag": "carousel",
          "data": {
            "chartDefinitions": {
              "a4aa175e-211f": {
                "type": "treemap",
                "legendPosition": "top",
                "title": {},
                "humanize": true,
                "dataSource": {
                  "labelRange": "'Top Categories'!C1:C51",
                  "type": "range",
                  "dataSets": [
                    { "dataSetId": "0", "dataRange": "'Top Categories'!A1:A51" }
                  ],
                  "dataSetsHaveTitle": false
                },
                "dataSetStyles": {}
              }
            },
            "title": {
              "fontSize": 21,
              "color": "#017E84",
              "text": "Top Categories",
              "italic": false,
              "bold": true
            },
            "items": [
              { "type": "chart", "chartId": "a4aa175e-211f" },
              {
                "type": "carouselDataView",
                "title": "Top 50",
                "rangeData": {
                  "_sheetId": "a254ea4a-b3ef",
                  "_zone": { "top": 0, "left": 0, "bottom": 50, "right": 2 }
                }
              }
            ],
            "fieldMatching": {}
          }
        },
        {
          "id": "ca658c8c-3da6",
          "col": 0,
          "row": 0,
          "offset": { "x": 0, "y": 125 },
          "width": 1000,
          "height": 407,
          "tag": "carousel",
          "data": {
            "chartDefinitions": {
              "0c5e3c79-3754-41a9-83df-b185003ce0b1": {
                "title": { "text": "" },
                "legendPosition": "none",
                "type": "line",
                "stacked": false,
                "axesDesign": {
                  "y": {
                    "title": { "text": "Revenue" }
                  }
                },
                "fillArea": true,
                "humanize": true,
                "dataSource": {
                  "type": "odoo",
                  "cumulatedStart": false,
                  "metaData": {
                    "groupBy": ["date:month"],
                    "measure": "price_subtotal",
                    "order": null,
                    "resModel": "sale.report",
                    "mode": "line",
                    "cumulatedStart": false
                  },
                  "searchParams": {
                    "comparison": null,
                    "context": {
                      "search_default_Sales": 1,
                      "group_by": [],
                      "search_default_filter_order_date": 1,
                      "search_default_recurring": 0,
                      "search_default_non_recurring": 1
                    },
                    "domain": [
                      [
                        "state",
                        "not in",
                        ["draft", "cancel", "sent"]
                      ]
                    ],
                    "groupBy": ["date:month"],
                    "orderBy": []
                  }
                },
                "dataSetStyles": {}
              }
            },
            "items": [
              { "type": "chart", "chartId": "0c5e3c79-3754-41a9-83df-b185003ce0b1" }
            ],
            "fieldMatching": {
              "0c5e3c79-3754-41a9-83df-b185003ce0b1": {
                "eefac62b-900a-4197-95e9-9a4cdbb832d6": { "chain": "date", "type": "datetime", "offset": 0 },
                "70f31046-f26e-4847-b177-d09937e4b674": { "chain": "website_id", "type": "many2one" },
                "cd428d80-466a-47b0-8af7-0393cd814d44": { "chain": "country_id", "type": "many2one" },
                "d24e0ac3-8117-4d2e-a0e6-4f650672916e": { "chain": "product_tmpl_id", "type": "many2one" },
                "2401236d-e945-48c2-b998-2533a8dcf1a0": { "chain": "partner_id", "type": "many2one" },
                "289948d3-96db-4067-8fd6-51b5b75e677c": { "chain": "categ_id", "type": "many2one" }
              }
            }
          }
        },
        {
          "id": "1bd1e01d-d845",
          "col": 0,
          "row": 0,
          "offset": { "x": 0, "y": 542 },
          "width": 495,
          "height": 407,
          "tag": "carousel",
          "data": {
            "chartDefinitions": {},
            "title": {
              "text": "Top Products",
              "bold": true,
              "fontSize": 21,
              "color": "#01666B"
            },
            "items": [
              {
                "type": "carouselDataView",
                "rangeData": {
                  "_sheetId": "7aded3e1-c2dc",
                  "_zone": { "top": 0, "left": 0, "bottom": 50, "right": 2 }
                }
              }
            ],
            "fieldMatching": {}
          }
        }
      ],
      "tables": [],
      "areGridLinesVisible": true,
      "isVisible": true,
      "backgroundColor": "#F9FAFB",
      "headerGroups": {
        "ROW": [],
        "COL": []
      },
      "comments": {}
    },
    {
      "id": "795f40fb-7598-4275-b0a8-549499781f22",
      "name": "Data",
      "colNumber": 26,
      "rowNumber": 100,
      "rows": {},
      "cols": {
        "0": { "size": 109 }
      },
      "merges": [],
      "cells": {
        "A1": "=_t(\"KPI\")",
        "A2": "=_t(\"Carts\")",
        "A3": "=_t(\"Orders\")",
        "A4": "=_t(\"Abandoned Carts\")",
        "A5": "=_t(\"Revenue\")",
        "B1": "=_t(\"Current\")",
        "B2": "=B3+B4",
        "B3": "=PIVOT.VALUE(7,\"order_reference\")",
        "B4": "=PIVOT.VALUE(2,\"order_reference\",\"is_abandoned_cart\",\"true\")",
        "B5": "=PIVOT.VALUE(5,\"price_subtotal\")",
        "C1": "=_t(\"Previous\")",
        "C2": "=C3+C4",
        "C3": "=PIVOT.VALUE(8,\"order_reference\")",
        "C4": "=PIVOT.VALUE(3,\"order_reference\",\"is_abandoned_cart\",\"true\")",
        "C5": "=PIVOT.VALUE(6,\"price_subtotal\")",
        "D1": "=_t(\"Current\")",
        "D2": "=FORMAT.LARGE.NUMBER(B2)",
        "D3:D5": { "R": "+R1" },
        "E1": "=_t(\"Previous\")",
        "E2": "=FORMAT.LARGE.NUMBER(C2)",
        "E3:E5": { "R": "+R1" }
      },
      "styles": { "A1:E1": 1 },
      "formats": {},
      "borders": {},
      "conditionalFormats": [],
      "dataValidationRules": [],
      "figures": [],
      "tables": [],
      "areGridLinesVisible": true,
      "isVisible": true,
      "headerGroups": {
        "ROW": [],
        "COL": []
      },
      "comments": {}
    },
    {
      "id": "7aded3e1-c2dc",
      "name": "Top Products",
      "colNumber": 26,
      "rowNumber": 100,
      "rows": {
        "0": { "size": 28 },
        "1": { "size": 28 },
        "2": { "size": 28 },
        "3": { "size": 28 },
        "4": { "size": 28 },
        "5": { "size": 28 },
        "6": { "size": 28 },
        "7": { "size": 28 },
        "8": { "size": 28 },
        "9": { "size": 28 },
        "10": { "size": 28 },
        "11": { "size": 28 },
        "12": { "size": 28 },
        "13": { "size": 28 },
        "14": { "size": 28 },
        "15": { "size": 28 },
        "16": { "size": 28 },
        "17": { "size": 28 },
        "18": { "size": 28 },
        "19": { "size": 28 },
        "20": { "size": 28 },
        "21": { "size": 28 },
        "22": { "size": 28 },
        "23": { "size": 28 },
        "24": { "size": 28 },
        "25": { "size": 28 },
        "26": { "size": 28 },
        "27": { "size": 28 },
        "28": { "size": 28 },
        "29": { "size": 28 },
        "30": { "size": 28 },
        "31": { "size": 28 },
        "32": { "size": 28 },
        "33": { "size": 28 },
        "34": { "size": 28 },
        "35": { "size": 28 },
        "36": { "size": 28 },
        "37": { "size": 28 },
        "38": { "size": 28 },
        "39": { "size": 28 },
        "40": { "size": 28 },
        "41": { "size": 28 },
        "42": { "size": 28 },
        "43": { "size": 28 },
        "44": { "size": 28 },
        "45": { "size": 28 },
        "46": { "size": 28 },
        "47": { "size": 28 },
        "48": { "size": 28 },
        "49": { "size": 28 },
        "50": { "size": 28 }
      },
      "cols": {
        "0": { "size": 287 }
      },
      "merges": [],
      "cells": { "A1": "=PIVOT(4,50,FALSE,FALSE)" },
      "styles": { "A1": 2, "A2:A51": 3, "B4:C51": 3, "B1:C1": 4, "B2:C3": 5 },
      "formats": { "A2:A13": 1, "C2:C51": 2 },
      "borders": {},
      "conditionalFormats": [
        {
          "id": "3dc45821-c5d2",
          "rule": { "type": "DataBarRule", "color": 14609659, "rangeValues": "C2:C51" },
          "ranges": ["A2:A51"]
        }
      ],
      "dataValidationRules": [],
      "figures": [],
      "tables": [],
      "areGridLinesVisible": true,
      "isVisible": true,
      "isLocked": false,
      "panes": { "xSplit": 0, "ySplit": 1 },
      "headerGroups": {
        "ROW": [],
        "COL": []
      },
      "defaultStyle": {
        "colDefault": { "0": 7 },
        "rowDefault": {},
        "sheetDefault": 6
      },
      "comments": {}
    },
    {
      "id": "a254ea4a-b3ef",
      "name": "Top Categories",
      "colNumber": 26,
      "rowNumber": 100,
      "rows": {
        "0": { "size": 28 },
        "1": { "size": 28 },
        "2": { "size": 28 },
        "3": { "size": 28 },
        "4": { "size": 28 },
        "5": { "size": 28 },
        "6": { "size": 28 },
        "7": { "size": 28 },
        "8": { "size": 28 },
        "9": { "size": 28 },
        "10": { "size": 28 },
        "11": { "size": 28 },
        "12": { "size": 28 },
        "13": { "size": 28 },
        "14": { "size": 28 },
        "15": { "size": 28 },
        "16": { "size": 28 },
        "17": { "size": 28 },
        "18": { "size": 28 },
        "19": { "size": 28 },
        "20": { "size": 28 },
        "21": { "size": 28 },
        "22": { "size": 28 },
        "23": { "size": 28 },
        "24": { "size": 28 },
        "25": { "size": 28 },
        "26": { "size": 28 },
        "27": { "size": 28 },
        "28": { "size": 28 },
        "29": { "size": 28 },
        "30": { "size": 28 },
        "31": { "size": 28 },
        "32": { "size": 28 },
        "33": { "size": 28 },
        "34": { "size": 28 },
        "35": { "size": 28 },
        "36": { "size": 28 },
        "37": { "size": 28 },
        "38": { "size": 28 },
        "39": { "size": 28 },
        "40": { "size": 28 },
        "41": { "size": 28 },
        "42": { "size": 28 },
        "43": { "size": 28 },
        "44": { "size": 28 },
        "45": { "size": 28 },
        "46": { "size": 28 },
        "47": { "size": 28 },
        "48": { "size": 28 },
        "49": { "size": 28 },
        "50": { "size": 28 }
      },
      "cols": {
        "0": { "size": 287 }
      },
      "merges": [],
      "cells": { "A1": "=PIVOT(1,50,FALSE,FALSE)" },
      "styles": { "A1": 2, "A2:A51": 3, "B4:C51": 3, "B1:C1": 4, "B2:C3": 5 },
      "formats": { "A2:A13": 1, "C2:C51": 2 },
      "borders": {},
      "conditionalFormats": [
        {
          "id": "3dc45821-c5d2",
          "rule": { "type": "DataBarRule", "color": 14609659, "rangeValues": "C2:C51" },
          "ranges": ["A2:A51"]
        }
      ],
      "dataValidationRules": [],
      "figures": [],
      "tables": [],
      "areGridLinesVisible": true,
      "isVisible": true,
      "isLocked": false,
      "panes": { "xSplit": 0, "ySplit": 1 },
      "headerGroups": {
        "ROW": [],
        "COL": []
      },
      "defaultStyle": {
        "colDefault": { "0": 7 },
        "rowDefault": {},
        "sheetDefault": 6
      },
      "comments": {}
    }
  ],
  "styles": {
    "1": { "bold": true },
    "2": { "bold": true, "align": "left", "verticalAlign": "top", "fontSize": 11 },
    "3": { "verticalAlign": "middle" },
    "4": {
      "bold": true,
      "align": "center",
      "verticalAlign": "top",
      "fontSize": 11,
      "textColor": "#434343"
    },
    "5": { "verticalAlign": "middle", "textColor": "#434343" },
    "6": {},
    "7": { "textColor": "#434343" }
  },
  "formats": { "1": "@", "2": "[$$]#,##0.00" },
  "borders": {},
  "revisionId": "START_REVISION",
  "uniqueFigureIds": true,
  "settings": {
    "locale": {
      "name": "English (US)",
      "code": "en_US",
      "thousandsSeparator": ",",
      "decimalSeparator": ".",
      "dateFormat": "mm/dd/yyyy",
      "timeFormat": "hh:mm:ss",
      "formulaArgSeparator": ",",
      "weekStart": 7
    }
  },
  "pivots": {
    "1": {
      "type": "ODOO",
      "fieldMatching": {
        "eefac62b-900a-4197-95e9-9a4cdbb832d6": { "chain": "date", "type": "datetime", "offset": 0 },
        "70f31046-f26e-4847-b177-d09937e4b674": { "chain": "website_id", "type": "many2one" },
        "cd428d80-466a-47b0-8af7-0393cd814d44": { "chain": "country_id", "type": "many2one" },
        "d24e0ac3-8117-4d2e-a0e6-4f650672916e": { "chain": "product_tmpl_id", "type": "many2one" },
        "2401236d-e945-48c2-b998-2533a8dcf1a0": { "chain": "partner_id", "type": "many2one" },
        "289948d3-96db-4067-8fd6-51b5b75e677c": { "chain": "categ_id", "type": "many2one" }
      },
      "context": {
        "search_default_Sales": 1,
        "group_by": [],
        "search_default_filter_order_date": 1,
        "search_default_recurring": 0,
        "search_default_non_recurring": 1
      },
      "domain": [
        [
          "state",
          "not in",
          ["draft", "cancel", "sent"]
        ]
      ],
      "id": "1",
      "measures": [
        {
          "id": "order_reference",
          "fieldName": "order_reference",
          "userDefinedName": "Units"
        },
        {
          "id": "price_subtotal",
          "fieldName": "price_subtotal",
          "userDefinedName": "Revenue"
        }
      ],
      "model": "sale.report",
      "name": "Categories",
      "sortedColumn": {
        "measure": "price_subtotal",
        "order": "desc",
        "domain": []
      },
      "formulaId": "1",
      "columns": [],
      "rows": [
        { "fieldName": "categ_id" }
      ]
    },
    "2": {
      "type": "ODOO",
      "fieldMatching": {
        "eefac62b-900a-4197-95e9-9a4cdbb832d6": { "chain": "date", "type": "datetime", "offset": 0 },
        "70f31046-f26e-4847-b177-d09937e4b674": { "chain": "website_id", "type": "many2one" },
        "cd428d80-466a-47b0-8af7-0393cd814d44": { "chain": "country_id", "type": "many2one" },
        "d24e0ac3-8117-4d2e-a0e6-4f650672916e": { "chain": "product_tmpl_id", "type": "many2one" },
        "2401236d-e945-48c2-b998-2533a8dcf1a0": { "chain": "partner_id", "type": "many2one" },
        "289948d3-96db-4067-8fd6-51b5b75e677c": { "chain": "categ_id", "type": "many2one" }
      },
      "context": {},
      "domain": [
        ["website_id", "!=", false]
      ],
      "id": "2",
      "measures": [
        { "id": "order_reference", "fieldName": "order_reference" },
        { "id": "price_subtotal", "fieldName": "price_subtotal" }
      ],
      "model": "sale.report",
      "name": "Sales Analysis by Abandoned Cart",
      "formulaId": "2",
      "columns": [],
      "rows": [
        { "fieldName": "is_abandoned_cart" }
      ]
    },
    "3": {
      "type": "ODOO",
      "fieldMatching": {
        "eefac62b-900a-4197-95e9-9a4cdbb832d6": { "chain": "date", "type": "datetime", "offset": -1 },
        "70f31046-f26e-4847-b177-d09937e4b674": { "chain": "website_id", "type": "many2one" },
        "cd428d80-466a-47b0-8af7-0393cd814d44": { "chain": "country_id", "type": "many2one" },
        "d24e0ac3-8117-4d2e-a0e6-4f650672916e": { "chain": "product_tmpl_id", "type": "many2one" },
        "2401236d-e945-48c2-b998-2533a8dcf1a0": { "chain": "partner_id", "type": "many2one" },
        "289948d3-96db-4067-8fd6-51b5b75e677c": { "chain": "categ_id", "type": "many2one" }
      },
      "context": { "search_default_confirmed": 1 },
      "domain": [
        ["website_id", "!=", false]
      ],
      "id": "3",
      "measures": [
        { "id": "order_reference", "fieldName": "order_reference" },
        { "id": "price_subtotal", "fieldName": "price_subtotal" }
      ],
      "model": "sale.report",
      "name": "Sales Analysis by Abandoned Cart",
      "formulaId": "3",
      "columns": [],
      "rows": [
        { "fieldName": "is_abandoned_cart" }
      ]
    },
    "4": {
      "type": "ODOO",
      "fieldMatching": {
        "eefac62b-900a-4197-95e9-9a4cdbb832d6": { "chain": "date", "type": "datetime", "offset": 0 },
        "70f31046-f26e-4847-b177-d09937e4b674": { "chain": "website_id", "type": "many2one" },
        "cd428d80-466a-47b0-8af7-0393cd814d44": { "chain": "country_id", "type": "many2one" },
        "d24e0ac3-8117-4d2e-a0e6-4f650672916e": { "chain": "product_tmpl_id", "type": "many2one" },
        "2401236d-e945-48c2-b998-2533a8dcf1a0": { "chain": "partner_id", "type": "many2one" },
        "289948d3-96db-4067-8fd6-51b5b75e677c": { "chain": "categ_id", "type": "many2one" }
      },
      "context": {},
      "domain": [
        "&",
        ["website_id", "!=", false],
        [
          "state",
          "in",
          ["sale", "done"]
        ]
      ],
      "id": "4",
      "measures": [
        {
          "id": "order_reference",
          "fieldName": "order_reference",
          "userDefinedName": "Units"
        },
        {
          "id": "price_subtotal",
          "fieldName": "price_subtotal",
          "userDefinedName": "Revenue"
        }
      ],
      "model": "sale.report",
      "name": "Products",
      "sortedColumn": {
        "measure": "price_subtotal",
        "order": "desc",
        "domain": []
      },
      "formulaId": "4",
      "columns": [],
      "rows": [
        { "fieldName": "product_id" }
      ]
    },
    "5": {
      "type": "ODOO",
      "fieldMatching": {
        "eefac62b-900a-4197-95e9-9a4cdbb832d6": { "chain": "date", "type": "datetime", "offset": 0 },
        "70f31046-f26e-4847-b177-d09937e4b674": { "chain": "website_id", "type": "many2one" },
        "cd428d80-466a-47b0-8af7-0393cd814d44": { "chain": "country_id", "type": "many2one" },
        "d24e0ac3-8117-4d2e-a0e6-4f650672916e": { "chain": "product_tmpl_id", "type": "many2one" },
        "2401236d-e945-48c2-b998-2533a8dcf1a0": { "chain": "partner_id", "type": "many2one" },
        "289948d3-96db-4067-8fd6-51b5b75e677c": { "chain": "categ_id", "type": "many2one" }
      },
      "context": {},
      "domain": [
        "&",
        ["website_id", "!=", false],
        [
          "state",
          "in",
          ["sale", "done"]
        ]
      ],
      "id": "5",
      "measures": [
        { "id": "price_subtotal", "fieldName": "price_subtotal" }
      ],
      "model": "sale.report",
      "name": "Sales Analysis",
      "sortedColumn": null,
      "formulaId": "5",
      "columns": [],
      "rows": []
    },
    "6": {
      "type": "ODOO",
      "fieldMatching": {
        "eefac62b-900a-4197-95e9-9a4cdbb832d6": { "chain": "date", "type": "datetime", "offset": -1 },
        "70f31046-f26e-4847-b177-d09937e4b674": { "chain": "website_id", "type": "many2one" },
        "cd428d80-466a-47b0-8af7-0393cd814d44": { "chain": "country_id", "type": "many2one" },
        "d24e0ac3-8117-4d2e-a0e6-4f650672916e": { "chain": "product_tmpl_id", "type": "many2one" },
        "2401236d-e945-48c2-b998-2533a8dcf1a0": { "chain": "partner_id", "type": "many2one" },
        "289948d3-96db-4067-8fd6-51b5b75e677c": { "chain": "categ_id", "type": "many2one" }
      },
      "context": { "search_default_confirmed": 1 },
      "domain": [
        "&",
        ["website_id", "!=", false],
        [
          "state",
          "in",
          ["sale", "done"]
        ]
      ],
      "id": "6",
      "measures": [
        { "id": "price_subtotal", "fieldName": "price_subtotal" }
      ],
      "model": "sale.report",
      "name": "Sales Analysis",
      "sortedColumn": null,
      "formulaId": "6",
      "columns": [],
      "rows": []
    },
    "7": {
      "type": "ODOO",
      "fieldMatching": {
        "eefac62b-900a-4197-95e9-9a4cdbb832d6": { "chain": "date", "type": "datetime", "offset": 0 },
        "70f31046-f26e-4847-b177-d09937e4b674": { "chain": "website_id", "type": "many2one" },
        "cd428d80-466a-47b0-8af7-0393cd814d44": { "chain": "country_id", "type": "many2one" },
        "d24e0ac3-8117-4d2e-a0e6-4f650672916e": { "chain": "product_tmpl_id", "type": "many2one" },
        "2401236d-e945-48c2-b998-2533a8dcf1a0": { "chain": "partner_id", "type": "many2one" },
        "289948d3-96db-4067-8fd6-51b5b75e677c": { "chain": "categ_id", "type": "many2one" }
      },
      "context": {},
      "domain": [
        "&",
        ["website_id", "!=", false],
        [
          "state",
          "in",
          ["sale", "done"]
        ]
      ],
      "id": "7",
      "measures": [
        { "id": "order_reference", "fieldName": "order_reference" }
      ],
      "model": "sale.report",
      "name": "Sales Analysis",
      "sortedColumn": null,
      "formulaId": "7",
      "columns": [],
      "rows": []
    },
    "8": {
      "type": "ODOO",
      "fieldMatching": {
        "eefac62b-900a-4197-95e9-9a4cdbb832d6": { "chain": "date", "type": "datetime", "offset": -1 },
        "70f31046-f26e-4847-b177-d09937e4b674": { "chain": "website_id", "type": "many2one" },
        "cd428d80-466a-47b0-8af7-0393cd814d44": { "chain": "country_id", "type": "many2one" },
        "d24e0ac3-8117-4d2e-a0e6-4f650672916e": { "chain": "product_tmpl_id", "type": "many2one" },
        "2401236d-e945-48c2-b998-2533a8dcf1a0": { "chain": "partner_id", "type": "many2one" },
        "289948d3-96db-4067-8fd6-51b5b75e677c": { "chain": "categ_id", "type": "many2one" }
      },
      "context": { "search_default_confirmed": 1 },
      "domain": [
        "&",
        ["website_id", "!=", false],
        [
          "state",
          "in",
          ["sale", "done"]
        ]
      ],
      "id": "8",
      "measures": [
        { "id": "order_reference", "fieldName": "order_reference" }
      ],
      "model": "sale.report",
      "name": "Sales Analysis",
      "sortedColumn": null,
      "formulaId": "8",
      "columns": [],
      "rows": []
    }
  },
  "pivotNextId": 9,
  "customTableStyles": {},
  "namedRanges": {},
  "globalFilters": [
    {
      "id": "eefac62b-900a-4197-95e9-9a4cdbb832d6",
      "type": "date",
      "label": "Period",
      "defaultValue": "last_7_days"
    },
    {
      "id": "70f31046-f26e-4847-b177-d09937e4b674",
      "type": "relation",
      "label": "Website",
      "defaultValueDisplayNames": [],
      "modelName": "website"
    },
    {
      "id": "cd428d80-466a-47b0-8af7-0393cd814d44",
      "type": "relation",
      "label": "Country",
      "defaultValueDisplayNames": [],
      "modelName": "res.country"
    },
    {
      "id": "d24e0ac3-8117-4d2e-a0e6-4f650672916e",
      "type": "relation",
      "label": "Product",
      "defaultValueDisplayNames": [],
      "modelName": "product.template"
    },
    {
      "id": "2401236d-e945-48c2-b998-2533a8dcf1a0",
      "type": "relation",
      "label": "Customer",
      "defaultValueDisplayNames": [],
      "modelName": "res.partner"
    },
    {
      "id": "289948d3-96db-4067-8fd6-51b5b75e677c",
      "type": "relation",
      "label": "Category",
      "defaultValueDisplayNames": [],
      "modelName": "product.category"
    }
  ],
  "lists": {},
  "listNextId": 1,
  "odooLinkReferences": {
    "0c5e3c79-3754-41a9-83df-b185003ce0b1": { "type": "odooMenu", "odooMenuId": "website.menu_website_dashboard" },
    "a761d77e-17d1-4d7a-ac85-5494c07dd360": { "type": "odooMenu", "odooMenuId": "website.menu_website_dashboard" },
    "7db1cb48-a155-4984-b8dd-de155db2b65f": { "type": "odooMenu", "odooMenuId": "website.menu_website_dashboard" },
    "1bfef494-7090-4263-8e07-83f14f43c0e7": { "type": "odooMenu", "odooMenuId": "website.menu_website_dashboard" },
    "79d91c01-7aeb-4845-aa82-5a41895b74af": { "type": "odooMenu", "odooMenuId": "website.menu_website_dashboard" }
  }
}

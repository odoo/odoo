odoo.define('accountcore.table2excel', function (require) {
    'use strict';
    (function ($, window, document, undefined) {
        var pluginName = "table2excel",
            defaults = {
                exclude: ".noExl",
                name: "Table2Excel",
                filename: "table2excel",
                fileext: ".xls",
                exclude_img: false,
                exclude_links: true,
                exclude_inputs: true,
                preserveColors: true
            };
        // The actual plugin constructor
        function Plugin(element, options) {
            this.element = element;
            // jQuery has an extend method which merges the contents of two or
            // more objects, storing the result in the first object. The first object
            // is generally empty as we don't want to alter the default options for
            // future instances of the plugin
            //
            this.settings = $.extend({}, defaults, options);
            this._defaults = defaults;
            this._name = pluginName;
            this.init();
        }
        Plugin.prototype = {
            init: function () {
                var e = this;
                var utf8Heading = "<meta http-equiv=\"content-type\" content=\"application/vnd.ms-excel; charset=UTF-8\">";
                e.template = {
                    head: "<html xmlns:o=\"urn:schemas-microsoft-com:office:office\" xmlns:x=\"urn:schemas-microsoft-com:office:excel\" xmlns=\"http://www.w3.org/TR/REC-html40\">" + utf8Heading + "<head><!--[if gte mso 9]><xml><x:ExcelWorkbook><x:ExcelWorksheets>",
                    sheet: {
                        head: "<x:ExcelWorksheet><x:Name>",
                        tail: "</x:Name><x:WorksheetOptions><x:DisplayGridlines/></x:WorksheetOptions></x:ExcelWorksheet>"
                    },
                    mid: "</x:ExcelWorksheets></x:ExcelWorkbook></xml><![endif]--></head><body>",
                    table: {
                        head: "<table>",
                        tail: "</table>"
                    },
                    foot: "</body></html>"
                };
                e.tableRows = [];
                // Styling variables
                var additionalStyles = "";
                var compStyle = null;
                // get contents of table except for exclude
                $(e.element).each(function (i, o) {
                    var tempRows = "";
                    $(o).find("tr").not(e.settings.exclude).each(function (i, p) {
                        // Reset for this row
                        additionalStyles = "";
                        // Preserve background and text colors on the row
                        if (e.settings.preserveColors) {
                            compStyle = getComputedStyle(p);
                            additionalStyles += (compStyle && compStyle.backgroundColor ? "background-color: " + compStyle.backgroundColor + ";" : "");
                            additionalStyles += (compStyle && compStyle.color ? "color: " + compStyle.color + ";" : "");
                        }
                        // Create HTML for Row
                        tempRows += "<tr style='" + additionalStyles + "'>";
                        // Loop through each TH and TD
                        $(p).find("td,th").not(e.settings.exclude).each(function (i, q) { // p did not exist, I corrected
                            // Reset for this column
                            additionalStyles = "";
                            // Preserve background and text colors on the row
                            if (e.settings.preserveColors) {
                                compStyle = getComputedStyle(q);
                                additionalStyles += (compStyle && compStyle.backgroundColor ? "background-color: " + compStyle.backgroundColor + ";" : "");
                                additionalStyles += (compStyle && compStyle.color ? "color: " + compStyle.color + ";" : "");
                            }
                            var rc = {
                                rows: $(this).attr("rowspan"),
                                cols: $(this).attr("colspan"),
                                flag: $(q).find(e.settings.exclude),
                                td_style: $(this).attr("style"),
                            };
                            if (rc.flag.length > 0) {
                                tempRows += "<td> </td>"; // exclude it!!
                            } else {
                                tempRows += "<td";
                                if (rc.rows > 0) {
                                    tempRows += " rowspan='" + rc.rows + "' ";
                                }
                                if (rc.cols > 0) {
                                    tempRows += " colspan='" + rc.cols + "' ";
                                }
                                if (additionalStyles) {
                                    tempRows += " style='" + additionalStyles + rc.td_style + "'";
                                }
                                tempRows += ">" + $(q).html() + "</td>";
                            }
                        });
                        tempRows += "</tr>";
                    });
                    // exclude img tags
                    if (e.settings.exclude_img) {
                        tempRows = exclude_img(tempRows);
                    }
                    // exclude link tags
                    if (e.settings.exclude_links) {
                        tempRows = exclude_links(tempRows);
                    }
                    // exclude input tags
                    if (e.settings.exclude_inputs) {
                        tempRows = exclude_inputs(tempRows);
                    }
                    e.tableRows.push(tempRows);
                });
                e.tableToExcel(e.tableRows, e.settings.name, e.settings.sheetName);
            },
            tableToExcel: function (table, name, sheetName) {
                var e = this,
                    fullTemplate = "",
                    i, link, a;
                e.format = function (s, c) {
                    return s.replace(/{(\w+)}/g, function (m, p) {
                        return c[p];
                    });
                };
                sheetName = typeof sheetName === "undefined" ? "Sheet" : sheetName;
                e.ctx = {
                    worksheet: name || "Worksheet",
                    table: table,
                    sheetName: sheetName
                };
                fullTemplate = e.template.head;
                if ($.isArray(table)) {
                    Object.keys(table).forEach(function (i) {
                        //fullTemplate += e.template.sheet.head + "{worksheet" + i + "}" + e.template.sheet.tail;
                        fullTemplate += e.template.sheet.head + sheetName + i + e.template.sheet.tail;
                    });
                }
                fullTemplate += e.template.mid;
                if ($.isArray(table)) {
                    Object.keys(table).forEach(function (i) {
                        fullTemplate += e.template.table.head + "{table" + i + "}" + e.template.table.tail;
                    });
                }
                fullTemplate += e.template.foot;
                for (i in table) {
                    e.ctx["table" + i] = table[i];
                }
                delete e.ctx.table;
                var isIE = navigator.appVersion.indexOf("MSIE 10") !== -1 || (navigator.userAgent.indexOf("Trident") !== -1 && navigator.userAgent.indexOf("rv:11") !== -1); // this works with IE10 and IE11 both :)
                //if (typeof msie !== "undefined" && msie > 0 || !!navigator.userAgent.match(/Trident.*rv\:11\./))      // this works ONLY with IE 11!!!
                if (isIE) {
                    if (typeof Blob !== "undefined") {
                        //use blobs if we can
                        fullTemplate = e.format(fullTemplate, e.ctx); // with this, works with IE
                        fullTemplate = [fullTemplate];
                        //convert to array
                        var blob1 = new Blob(fullTemplate, {
                            type: "text/html"
                        });
                        window.navigator.msSaveBlob(blob1, getFileName(e.settings));
                    } else {
                        //otherwise use the iframe and save
                        //requires a blank iframe on page called txtArea1
                        txtArea1.document.open("text/html", "replace");
                        txtArea1.document.write(e.format(fullTemplate, e.ctx));
                        txtArea1.document.close();
                        txtArea1.focus();
                        sa = txtArea1.document.execCommand("SaveAs", true, getFileName(e.settings));
                    }
                } else {
                    var blob = new Blob([e.format(fullTemplate, e.ctx)], {
                        type: "application/vnd.ms-excel"
                    });
                    window.URL = window.URL || window.webkitURL;
                    link = window.URL.createObjectURL(blob);
                    a = document.createElement("a");
                    a.download = getFileName(e.settings);
                    a.href = link;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                }
                return true;
            }
        };

        function getFileName(settings) {
            return (settings.filename ? settings.filename : "table2excel");
        }
        // Removes all img tags
        function exclude_img(string) {
            var _patt = /(\s+alt\s*=\s*"([^"]*)"|\s+alt\s*=\s*'([^']*)')/i;
            return string.replace(/<img[^>]*>/gi, function myFunction(x) {
                var res = _patt.exec(x);
                if (res !== null && res.length >= 2) {
                    return res[2];
                } else {
                    return "";
                }
            });
        }
        // Removes all link tags
        function exclude_links(string) {
            return string.replace(/<a[^>]*>|<\/a>/gi, "");
        }
        // Removes input params
        function exclude_inputs(string) {
            var _patt = /(\s+value\s*=\s*"([^"]*)"|\s+value\s*=\s*'([^']*)')/i;
            return string.replace(/<input[^>]*>|<\/input>/gi, function myFunction(x) {
                var res = _patt.exec(x);
                if (res !== null && res.length >= 2) {
                    return res[2];
                } else {
                    return "";
                }
            });
        }
        $.fn[pluginName] = function (options) {
            var e = this;
            e.each(function () {
                if (!$.data(e, "plugin_" + pluginName)) {
                    $.data(e, "plugin_" + pluginName, new Plugin(this, options));
                }
            });
            // chain jQuery functions
            return e;
        };
        // return pluginName;
    })(jQuery, window, document);
});
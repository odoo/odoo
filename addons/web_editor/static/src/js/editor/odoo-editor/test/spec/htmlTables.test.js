import {
    BasicEditor,
    testEditor,
    pasteHtml,
} from "../utils.js";

// The tests below are very sensitive to whitespaces as they do represent actual
// whitespace text nodes in the DOM. The tests will fail if those are removed.

describe('Paste HTML tables', () => {
    describe('From Microsoft Excel Online', async () => {
        it('should keep all allowed style (Excel Online)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>[]</p>',
                stepFunction: async editor => {
                    await pasteHtml(editor,
`<div ccp_infra_version='3' ccp_infra_timestamp='1684505961078' ccp_infra_user_hash='540904553' ccp_infra_copy_id=''
    data-ccp-timestamp='1684505961078'>
    <html>

    <head>
        <meta http-equiv=Content-Type content="text/html; charset=utf-8">
        <meta name=ProgId content=Excel.Sheet>
        <meta name=Generator content="Microsoft Excel 15">
        <style>
            table {
                mso-displayed-decimal-separator: "\\,";
                mso-displayed-thousand-separator: "\\.";
            }

            tr {
                mso-height-source: auto;
            }

            col {
                mso-width-source: auto;
            }

            td {
                padding-top: 1px;
                padding-right: 1px;
                padding-left: 1px;
                mso-ignore: padding;
                color: black;
                font-size: 11.0pt;
                font-weight: 400;
                font-style: normal;
                text-decoration: none;
                font-family: Calibri, sans-serif;
                mso-font-charset: 0;
                text-align: general;
                vertical-align: bottom;
                border: none;
                white-space: nowrap;
                mso-rotate: 0;
            }

            .font12 {
                color: #495057;
                font-size: 10.0pt;
                font-weight: 400;
                font-style: italic;
                text-decoration: none;
                font-family: "Odoo Unicode Support Noto";
                mso-generic-font-family: auto;
                mso-font-charset: 0;
            }

            .font13 {
                color: #495057;
                font-size: 10.0pt;
                font-weight: 700;
                font-style: italic;
                text-decoration: none;
                font-family: "Odoo Unicode Support Noto";
                mso-generic-font-family: auto;
                mso-font-charset: 0;
            }

            .font33 {
                color: #495057;
                font-size: 10.0pt;
                font-weight: 700;
                font-style: normal;
                text-decoration: none;
                font-family: "Odoo Unicode Support Noto";
                mso-generic-font-family: auto;
                mso-font-charset: 0;
            }

            .xl87 {
                font-size: 14.0pt;
                font-family: "Roboto Mono";
                mso-generic-font-family: auto;
                mso-font-charset: 1;
                text-align: center;
            }

            .xl88 {
                color: #495057;
                font-size: 10.0pt;
                font-style: italic;
                font-family: "Odoo Unicode Support Noto";
                mso-generic-font-family: auto;
                mso-font-charset: 0;
                text-align: center;
            }

            .xl89 {
                color: #495057;
                font-size: 10.0pt;
                font-style: italic;
                font-family: Arial;
                mso-generic-font-family: auto;
                mso-font-charset: 1;
                text-align: center;
            }

            .xl90 {
                color: #495057;
                font-size: 10.0pt;
                font-weight: 700;
                font-family: "Odoo Unicode Support Noto";
                mso-generic-font-family: auto;
                mso-font-charset: 0;
                text-align: center;
            }

            .xl91 {
                color: #495057;
                font-size: 10.0pt;
                font-weight: 700;
                text-decoration: underline;
                text-underline-style: single;
                font-family: Arial;
                mso-generic-font-family: auto;
                mso-font-charset: 1;
                text-align: center;
            }

            .xl92 {
                color: red;
                font-size: 10.0pt;
                font-family: Arial;
                mso-generic-font-family: auto;
                mso-font-charset: 1;
                text-align: center;
            }

            .xl93 {
                color: red;
                font-size: 10.0pt;
                text-decoration: underline;
                text-underline-style: single;
                font-family: Arial;
                mso-generic-font-family: auto;
                mso-font-charset: 1;
                text-align: center;
            }

            .xl94 {
                color: #495057;
                font-size: 10.0pt;
                font-family: "Odoo Unicode Support Noto";
                mso-generic-font-family: auto;
                mso-font-charset: 1;
                text-align: center;
                background: yellow;
                mso-pattern: black none;
            }

            .xl95 {
                color: red;
                font-size: 10.0pt;
                font-family: Arial;
                mso-generic-font-family: auto;
                mso-font-charset: 1;
                text-align: center;
                background: yellow;
                mso-pattern: black none;
                white-space: normal;
            }
        </style>
    </head>

    <body link="#0563C1" vlink="#954F72">
        <table width=398 style='border-collapse:collapse;width:299pt'><!--StartFragment-->
            <col width=187 style='width:140pt'>
            <col width=211 style='width:158pt'>
            <tr height=20 style='height:15.0pt'>
                <td width=187 height=20 class=xl88 dir=LTR style='width:140pt;height:15.0pt'><span class=font12>Italic
                        then also </span><span class=font13>BOLD</span></td>
                <td width=211 class=xl89 dir=LTR style='width:158pt'><s>Italic strike</s></td>
            </tr>
            <tr height=20 style='height:15.0pt'>
                <td height=20 class=xl90 dir=LTR style='height:15.0pt'><span class=font33>Just bold </span><span
                        class=font12>Just Italic</span></td>
                <td class=xl91 dir=LTR>Bold underline</td>
            </tr>
            <tr height=20 style='height:15.0pt'>
                <td height=20 class=xl92 dir=LTR style='height:15.0pt'>Color text</td>
                <td class=xl93 dir=LTR><s>Color strike and underline</s></td>
            </tr>
            <tr height=20 style='height:15.0pt'>
                <td height=20 class=xl94 dir=LTR style='height:15.0pt'>Color background</td>
                <td width=211 class=xl95 dir=LTR style='width:158pt'>Color text on color background</td>
            </tr>
            <tr height=27 style='height:20.25pt'>
                <td colspan=2 width=398 height=27 class=xl87 dir=LTR style='width:299pt;height:20.25pt'>14pt MONO TEXT
                </td>
            </tr><!--EndFragment-->
        </table>
    </body>

    </html>
</div>`,
                    );
                },
                contentAfter:
`<table class="table table-bordered">
            
            
            <tbody><tr>
                <td class="" style="color: #495057;font-size: 10.0pt;font-style: italic"><span class="" style="color: #495057;font-size: 10.0pt;font-weight: 400;font-style: italic;text-decoration: none">Italic
                        then also </span><span class="" style="color: #495057;font-size: 10.0pt;font-weight: 700;font-style: italic;text-decoration: none">BOLD</span></td>
                <td class="" style="color: #495057;font-size: 10.0pt;font-style: italic"><s>Italic strike</s></td>
            </tr>
            <tr>
                <td class="" style="color: #495057;font-size: 10.0pt;font-weight: 700"><span class="" style="color: #495057;font-size: 10.0pt;font-weight: 700;font-style: normal;text-decoration: none">Just bold </span><span class="" style="color: #495057;font-size: 10.0pt;font-weight: 400;font-style: italic;text-decoration: none">Just Italic</span></td>
                <td class="" style="color: #495057;font-size: 10.0pt;font-weight: 700;text-decoration: underline">Bold underline</td>
            </tr>
            <tr>
                <td class="" style="color: red;font-size: 10.0pt">Color text</td>
                <td class="" style="color: red;font-size: 10.0pt;text-decoration: underline"><s>Color strike and underline</s></td>
            </tr>
            <tr>
                <td class="" style="color: #495057;font-size: 10.0pt;background-color: yellow">Color background</td>
                <td class="" style="color: red;font-size: 10.0pt;background-color: yellow">Color text on color background</td>
            </tr>
            <tr>
                <td class="" style="font-size: 14.0pt">14pt MONO TEXT
                </td>
            </tr>
        </tbody></table><p>
    

    
[]</p>`,
            });
        });
    });
    describe('From Google Sheets', async () => {
        it('should keep all allowed style (Google Sheets)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>[]</p>',
                stepFunction: async editor => {
                    await pasteHtml(editor,
`<google-sheets-html-origin>
    <style type="text/css">
        td {
            border: 1px solid #cccccc;
        }

        br {
            mso-data-placement: same-cell;
        }
    </style>
    <table xmlns="http://www.w3.org/1999/xhtml" cellspacing="0" cellpadding="0" dir="ltr" border="1"
        style="table-layout:fixed;font-size:10pt;font-family:Arial;width:0px;border-collapse:collapse;border:none">
        <colgroup>
            <col width="170" />
            <col width="187" />
        </colgroup>
        <tbody>
            <tr style="height:21px;">
                <td style="overflow:hidden;padding:2px 3px 2px 3px;vertical-align:bottom;font-family:Odoo Unicode Support Noto;font-weight:normal;font-style:italic;color:#495057;"
                    data-sheets-value="{&quot;1&quot;:2,&quot;2&quot;:&quot;Italic then also BOLD&quot;}"
                    data-sheets-textstyleruns="{&quot;1&quot;:0,&quot;2&quot;:{&quot;3&quot;:&quot;Arial&quot;}}{&quot;1&quot;:17,&quot;2&quot;:{&quot;3&quot;:&quot;Arial&quot;,&quot;5&quot;:1}}">
                    <span style="font-size:10pt;font-family:Arial;font-style:italic;color:#495057;">Italic then also
                    </span><span
                        style="font-size:10pt;font-family:Arial;font-weight:bold;font-style:italic;color:#495057;">BOLD</span>
                </td>
                <td style="overflow:hidden;padding:2px 3px 2px 3px;vertical-align:bottom;font-style:italic;text-decoration:line-through;color:#495057;"
                    data-sheets-value="{&quot;1&quot;:2,&quot;2&quot;:&quot;Italic strike&quot;}">Italic strike</td>
            </tr>
            <tr style="height:21px;">
                <td style="overflow:hidden;padding:2px 3px 2px 3px;vertical-align:bottom;font-family:Odoo Unicode Support Noto;font-weight:bold;color:#495057;"
                    data-sheets-value="{&quot;1&quot;:2,&quot;2&quot;:&quot;Just bold Just italic&quot;}"
                    data-sheets-textstyleruns="{&quot;1&quot;:0,&quot;2&quot;:{&quot;3&quot;:&quot;Arial&quot;}}{&quot;1&quot;:10,&quot;2&quot;:{&quot;3&quot;:&quot;Arial&quot;,&quot;5&quot;:0,&quot;6&quot;:1}}">
                    <span
                        style="font-size:10pt;font-family:Arial;font-weight:bold;font-style:normal;color:#495057;">Just
                        Bold </span><span style="font-size:10pt;font-family:Arial;font-style:italic;color:#495057;">Just
                        Italic</span>
                </td>
                <td style="overflow:hidden;padding:2px 3px 2px 3px;vertical-align:bottom;font-weight:bold;text-decoration:underline;color:#495057;"
                    data-sheets-value="{&quot;1&quot;:2,&quot;2&quot;:&quot;Bold underline&quot;}">Bold underline</td>
            </tr>
            <tr style="height:21px;">
                <td style="overflow:hidden;padding:2px 3px 2px 3px;vertical-align:bottom;"
                    data-sheets-value="{&quot;1&quot;:2,&quot;2&quot;:&quot;Color text&quot;}"><span style="color:#ff0000;">Color text</span></td>
                <td style="overflow:hidden;padding:2px 3px 2px 3px;vertical-align:bottom;text-decoration:underline line-through;color:#ff0000;"
                    data-sheets-value="{&quot;1&quot;:2,&quot;2&quot;:&quot;Color strike and underline&quot;}">Color
                    strike and underline</td>
            </tr>
            <tr style="height:21px;">
                <td style="overflow:hidden;padding:2px 3px 2px 3px;vertical-align:bottom;background-color:#ffff00;font-family:Odoo Unicode Support Noto;font-weight:normal;color:#495057;"
                    data-sheets-value="{&quot;1&quot;:2,&quot;2&quot;:&quot;Color background&quot;}">Color background
                </td>
                <td style="overflow:hidden;padding:2px 3px 2px 3px;vertical-align:bottom;background-color:#ffff00;color:#ff0000;"
                    data-sheets-value="{&quot;1&quot;:2,&quot;2&quot;:&quot;Color text on color background&quot;}">Color
                    text on color background</td>
            </tr>
            <tr style="height:21px;">
                <td style="overflow:hidden;padding:2px 3px 2px 3px;vertical-align:bottom;font-family:Roboto Mono;font-size:14pt;font-weight:normal;text-align:center;"
                    rowspan="1" colspan="2"
                    data-sheets-value="{&quot;1&quot;:2,&quot;2&quot;:&quot;14pt MONO TEXT&quot;}">14pt MONO TEXT</td>
            </tr>
        </tbody>
    </table>
</google-sheets-html-origin>`
                    );
                },
                contentAfter:
`<table class="table table-bordered">
        
            
            
        
        <tbody>
            <tr>
                <td style="font-weight:normal;font-style:italic;color:#495057">
                    <span style="font-size:10pt;font-style:italic;color:#495057">Italic then also
                    </span><span style="font-size:10pt;font-weight:bold;font-style:italic;color:#495057">BOLD</span>
                </td>
                <td style="font-style:italic;text-decoration:line-through;color:#495057">Italic strike</td>
            </tr>
            <tr>
                <td style="font-weight:bold;color:#495057">
                    <span style="font-size:10pt;font-weight:bold;font-style:normal;color:#495057">Just
                        Bold </span><span style="font-size:10pt;font-style:italic;color:#495057">Just
                        Italic</span>
                </td>
                <td style="font-weight:bold;text-decoration:underline;color:#495057">Bold underline</td>
            </tr>
            <tr>
                <td><span style="color:#ff0000">Color text</span></td>
                <td style="text-decoration:underline line-through;color:#ff0000">Color
                    strike and underline</td>
            </tr>
            <tr>
                <td style="background-color:#ffff00;font-weight:normal;color:#495057">Color background
                </td>
                <td style="background-color:#ffff00;color:#ff0000">Color
                    text on color background</td>
            </tr>
            <tr>
                <td style="font-size:14pt;font-weight:normal">14pt MONO TEXT</td>
            </tr>
        </tbody>
    </table><p>
[]</p>`,
            });
        });
    });
    describe('From Libre Office', async () => {
        it('should keep all allowed style (Libre Office)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>[]</p>',
                stepFunction: async editor => {
                    await pasteHtml(editor,
`<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">
<html>

<head>
    <meta http-equiv="content-type" content="text/html; charset=utf-8" />
    <title></title>
    <meta name="generator" content="LibreOffice 6.4.7.2 (Linux)" />
    <style type="text/css">
        body,
        div,
        table,
        thead,
        tbody,
        tfoot,
        tr,
        th,
        td,
        p {
            font-family: "Arial";
            font-size: x-small
        }

        a.comment-indicator:hover+comment {
            background: #ffd;
            position: absolute;
            display: block;
            border: 1px solid black;
            padding: 0.5em;
        }

        a.comment-indicator {
            background: red;
            display: inline-block;
            border: 1px solid black;
            width: 0.5em;
            height: 0.5em;
        }

        comment {
            display: none;
        }
    </style>
</head>

<body>
    <table cellspacing="0" border="0">
        <colgroup width="212"></colgroup>
        <colgroup width="209"></colgroup>
        <tr>
            <td style="border-top: 1px solid #000000; border-bottom: 1px solid #000000; border-left: 1px solid #000000; border-right: 1px solid #000000"
                height="20" align="left"><i>Italic then also BOLD</i></td>
            <td style="border-top: 1px solid #000000; border-bottom: 1px solid #000000; border-left: 1px solid #000000; border-right: 1px solid #000000"
                align="left"><i><s>Italic strike</s></i></td>
        </tr>
        <tr>
            <td style="border-top: 1px solid #000000; border-bottom: 1px solid #000000; border-left: 1px solid #000000; border-right: 1px solid #000000"
                height="20" align="left"><b>Just bold Just italic</b></td>
            <td style="border-top: 1px solid #000000; border-bottom: 1px solid #000000; border-left: 1px solid #000000; border-right: 1px solid #000000"
                align="left"><b><u>Bold underline</u></b></td>
        </tr>
        <tr>
            <td style="border-top: 1px solid #000000; border-bottom: 1px solid #000000; border-left: 1px solid #000000; border-right: 1px solid #000000"
                height="20" align="left">
                <font color="#FF0000">Color text</font>
            </td>
            <td style="border-top: 1px solid #000000; border-bottom: 1px solid #000000; border-left: 1px solid #000000; border-right: 1px solid #000000"
                align="left"><u><s>
                        <font color="#FF0000">Color strike and underline</font>
                    </s></u></td>
        </tr>
        <tr>
            <td style="border-top: 1px solid #000000; border-bottom: 1px solid #000000; border-left: 1px solid #000000; border-right: 1px solid #000000"
                height="20" align="left" bgcolor="#FFFF00">Color background</td>
            <td style="border-top: 1px solid #000000; border-bottom: 1px solid #000000; border-left: 1px solid #000000; border-right: 1px solid #000000"
                align="left" bgcolor="#FFFF00">
                <font color="#FF0000">Color text on color background</font>
            </td>
        </tr>
        <tr>
            <td colspan=2 height="26" align="center" valign=middle>
                <font face="Andale Mono" size=4>14pt MONO TEXT</font>
            </td>
        </tr>
    </table>
</body>

</html>`
                    );
                },
                contentAfter:
`<table class="table table-bordered">
        
        
        <tbody><tr>
            <td><i>Italic then also BOLD</i></td>
            <td><i><s>Italic strike</s></i></td>
        </tr>
        <tr>
            <td><b>Just bold Just italic</b></td>
            <td><b><u>Bold underline</u></b></td>
        </tr>
        <tr>
            <td>
                <font style="color: rgb(255, 0, 0)">Color text</font>
            </td>
            <td><u><s>
                        <font style="color: rgb(255, 0, 0)">Color strike and underline</font>
                    </s></u></td>
        </tr>
        <tr>
            <td style="background-color: rgb(255, 255, 0)">Color background</td>
            <td style="background-color: rgb(255, 255, 0)">
                <font style="color: rgb(255, 0, 0)">Color text on color background</font>
            </td>
        </tr>
        <tr>
            <td>
                <font style="font-size: 14pt">14pt MONO TEXT</font>
            </td>
        </tr>
    </tbody></table><p>


[]</p>`,
            });
        });
    });
});

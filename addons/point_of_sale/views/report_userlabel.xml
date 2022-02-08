<?xml version="1.0" encoding="utf-8"?>
<odoo>
<template id="report_userlabel">
    <t t-call="web.basic_layout">
        <div class="page">
            <t t-foreach="docs" t-as="user">
                <div class="col-6 mb92">
                    <table class="table table-bordered">
                        <thead>
                            <tr>
                                <th class="col-4 danger"/>
                                <th class="active"/>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td><div t-if="user.barcode" t-field="user.barcode" t-options="{'widget': 'barcode', 'symbology': 'EAN13', 'width': 300, 'height': 50, 'img_style': 'width:100%;height:35%;'}"/></td>
                                <td><strong t-field="user.name"/></td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </t>
        </div>
    </t>
</template>
</odoo>

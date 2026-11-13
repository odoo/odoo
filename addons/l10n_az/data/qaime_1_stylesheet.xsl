<xsl:stylesheet id="stylesheet" version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <xsl:template match="xsl:stylesheet" />
    <xsl:template match="/root">
        <html>
            <head>
                <style> body {background-color: white; font-family:  Arial, sans-serif; } .paper {padding:5px; } table {width: 100%; font-size: 16px; } table tr td {padding: 10px 15px; text-align: left; width:50%; } .products table {border-collapse: collapse; font-size: 14px; } .products table th, #products table td  {border: 1px solid #000; padding: 10px; } .products table td {width:auto; border: 1px solid #000; text-align:center; } .products table th {text-align:center; } .noPadding {padding: 40px 0px; } .total tr :nth-child(odd) {width:40%; } .total tr :nth-child(even) {width:10%; } </style>
            </head>
            <body>
                <table class="paper">
                    <tr>
                        <td>Alan tərəfin VÖEN-i:</td>
                        <td>
                            <xsl:value-of select="qaimeKime" />
                        </td>
                    </tr>
                    <tr>
                        <td>Alan tərəfin adı:</td>
                        <td>
                            <xsl:value-of select="qaimeKimeAd" />
                        </td>
                    </tr>
                    <tr>
                        <td>Satan tərəfin VÖEN-i:</td>
                        <td>
                            <xsl:value-of select="qaimeKimden" />
                        </td>
                    </tr>
                    <tr>
                        <td>Qeyd</td>
                        <td>
                            <xsl:value-of select="des" />
                        </td>
                    </tr>
                    <tr>
                        <td>Əlavə qeyd</td>
                        <td>
                            <xsl:value-of select="des2" />
                        </td>
                    </tr>
                    <tr>
                        <td>Obyektin adı</td>
                        <td>
                            <xsl:value-of select="ma" />
                        </td>
                    </tr>
                    <tr>
                        <td>Obyektin kodu</td>
                        <td>
                            <xsl:value-of select="mk" />
                        </td>
                    </tr>
                    <tr>
                        <td class="products noPadding" colspan="2">
                            <table>
                                <thead>
                                    <th>Mal kodu</th>
                                    <th>Mal adı</th>
                                    <th>Bar kod</th>
                                    <th>Ölçü vahidi</th>
                                    <th>Malın miqdarı</th>
                                    <th>Malın buraxılış qiyməti</th>
                                    <th>Cəmi qiyməti</th>
                                    <th>Aksiz dərəcəsi</th>
                                    <th>Aksiz məbləği</th>
                                    <th>Cəmi məbləğ</th>
                                    <th>ƏDV-yə cəlb edilən məbləğ</th>
                                    <th>ƏDV-yə cəlb edilməyən məbləğ</th>
                                    <th>ƏDV-dən azad olunan</th>
                                    <th>ƏDV-yə 0 dərəcə ilə cəlb edilən məbləğ</th>
                                    <th>Ödənilməli ƏDV</th>
                                    <th>Yol vergisi məbləği</th>
                                    <th>Yekun məbləğ</th>
                                </thead>
                                <tbody class="productTable">
                                    <xsl:for-each select="product/qaimeTable/row">
                                        <tr>
                                            <td>
                                                <xsl:value-of select="c1" />
                                            </td>
                                            <td>
                                                <xsl:value-of select="c2" />
                                            </td>
                                            <td>
                                                <xsl:value-of select="c17" />
                                            </td>
                                            <td>
                                                <xsl:value-of select="c3" />
                                            </td>
                                            <td>
                                                <xsl:value-of select="c4" />
                                            </td>
                                            <td>
                                                <xsl:value-of select="c5" />
                                            </td>
                                            <td>
                                                <xsl:value-of select="c6" />
                                            </td>
                                            <td>
                                                <xsl:value-of select="c7" />
                                            </td>
                                            <td>
                                                <xsl:value-of select="c8" />
                                            </td>
                                            <td>
                                                <xsl:value-of select="c9" />
                                            </td>
                                            <td>
                                                <xsl:value-of select="c10" />
                                            </td>
                                            <td>
                                                <xsl:value-of select="c11" />
                                            </td>
                                            <td>
                                                <xsl:value-of select="c12" />
                                            </td>
                                            <td>
                                                <xsl:value-of select="c13" />
                                            </td>
                                            <td>
                                                <xsl:value-of select="c14" />
                                            </td>
                                            <td>
                                                <xsl:value-of select="c15" />
                                            </td>
                                            <td>
                                                <xsl:value-of select="c16" />
                                            </td>
                                        </tr>
                                    </xsl:for-each>
                                </tbody>
                            </table>
                        </td>
                    </tr>
                </table>
                <table class="total">
                    <tr>
                        <td>Malların cəmi qiyməti</td>
                        <td>
                            <xsl:value-of select="product/qaimeYekunTable/row/c1" />
                        </td>
                        <td>Malların cəmi məbləği</td>
                        <td>
                            <xsl:value-of select="product/qaimeYekunTable/row/c3" />
                        </td>
                    </tr>
                    <tr>
                        <td>Malların aksiz cəmi məbləği</td>
                        <td>
                            <xsl:value-of select="product/qaimeYekunTable/row/c2" />
                        </td>
                        <td>Malların ƏDV-yə cəlb edilən cəmi məbləği</td>
                        <td>
                            <xsl:value-of select="product/qaimeYekunTable/row/c4" />
                        </td>
                    </tr>
                    <tr>
                        <td>Malların cəmi ödənilməli ƏDV məbləği</td>
                        <td>
                            <xsl:value-of select="product/qaimeYekunTable/row/c8" />
                        </td>
                        <td>Malların  ƏDV-yə cəlb edilməyən cəmi məbləği </td>
                        <td>
                            <xsl:value-of select="product/qaimeYekunTable/row/c5" />
                        </td>
                    </tr>
                    <tr>
                        <td>ƏDV-dən azad olunan</td>
                        <td>
                            <xsl:value-of select="product/qaimeYekunTable/row/c6" />
                        </td>
                        <td>Malların  ƏDV-yə 0 dərəcə ilə cəlb edilən cəmi məbləği</td>
                        <td>
                            <xsl:value-of select="product/qaimeYekunTable/row/c7" />
                        </td>
                    </tr>
                    <tr>
                        <td>Yekun məbləğ</td>
                        <td>
                            <xsl:value-of select="product/qaimeYekunTable/row/c9" />
                        </td>
                        <td></td>
                        <td></td>
                    </tr>
                </table>
            </body>
        </html>
    </xsl:template>
</xsl:stylesheet>
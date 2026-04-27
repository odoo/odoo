<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="2.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:fn="http://www.w3.org/2005/xpath-functions" xmlns:detallista="http://www.sat.gob.mx/detallista">
    <!-- <xsl:output method="text" version="1.0" encoding="UTF-8" indent="no"/> -->
    <xsl:output method="text" version="1.0" encoding="UTF-8" indent="no"/>
<!-- Manejador de nodos tipo detallista -->
    <xsl:template match="detallista:detallista">
        <!-- Iniciamos el tratamiento de los atributos del sector detallista -->
        <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@documentStructureVersion"/>
        </xsl:call-template>
        <xsl:for-each select="detallista:orderIdentification/detallista:referenceIdentification">
            <xsl:call-template name="Requerido">
                <xsl:with-param name="valor" select="."/>
            </xsl:call-template>
        </xsl:for-each>
        <xsl:call-template name="Opcional">
            <xsl:with-param name="valor" select="detallista:orderIdentification/detallista:ReferenceDate"/>
        </xsl:call-template>
        <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="detallista:buyer/detallista:gln"/>
        </xsl:call-template>
        <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="detallista:seller/detallista:gln"/>
        </xsl:call-template>
        <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="detallista:seller/detallista:alternatePartyIdentification"/>
        </xsl:call-template>
        <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="detallista:totalAmount/detallista:Amount"/>
        </xsl:call-template>
        <xsl:for-each select="detallista:TotalAllowanceCharge/detallista:specialServicesType">
            <xsl:call-template name="Opcional">
                <xsl:with-param name="valor" select="."/>
            </xsl:call-template>
        </xsl:for-each>
        <xsl:for-each select="detallista:TotalAllowanceCharge/detallista:Amount">
            <xsl:call-template name="Opcional">
                <xsl:with-param name="valor" select="."/>
            </xsl:call-template>
        </xsl:for-each>
    </xsl:template>
</xsl:stylesheet>

<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:fn="http://www.w3.org/2005/xpath-functions" xmlns:ecc12="http://www.sat.gob.mx/EstadoDeCuentaCombustible12" version="2.0">
    <xsl:template match="ecc12:EstadoDeCuentaCombustible">

        <!-- Manejador de nodos tipo EstadoDeCuentaCombustible -->
        <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@Version"/>
        </xsl:call-template>
        <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@TipoOperacion"/>
        </xsl:call-template>
        <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@NumeroDeCuenta"/>
        </xsl:call-template>
        <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@SubTotal"/>
        </xsl:call-template>
        <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@Total"/>
        </xsl:call-template>

        <!--
            Iniciamos el manejo de los elementos hijo en la secuencia 
        -->
        <xsl:apply-templates select="./ecc12:Conceptos"/>

    </xsl:template>

    <xsl:template match="ecc12:Conceptos">
    <!--
        Iniciamos el tratamiento de los atributos de ecc12:ConceptoEstadoDeCuentaCombustible
    -->
        <xsl:for-each select="./ecc12:ConceptoEstadoDeCuentaCombustible">
            <xsl:apply-templates select="."/>
        </xsl:for-each>
    </xsl:template>

    <xsl:template match="ecc12:Traslados">
    <!--
        Iniciamos el tratamiento de los atributos de ecc12:Traslado
    -->
        <xsl:for-each select="./ecc12:Traslado">
            <xsl:apply-templates select="."/>
        </xsl:for-each>
    </xsl:template>

    <!--
        Iniciamos el manejo de los elementos hijo en la secuencia ConceptoEstadoDeCuentaCombustible
     -->
    <xsl:template match="ecc12:ConceptoEstadoDeCuentaCombustible">
    <!--   Iniciamos el manejo de los nodos dependientes  -->
        <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@Identificador"/>
        </xsl:call-template>
        <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@Fecha"/>
        </xsl:call-template>
        <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@Rfc"/>
        </xsl:call-template>
        <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@ClaveEstacion"/>
        </xsl:call-template>
        <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@Cantidad"/>
        </xsl:call-template>
        <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@TipoCombustible"/>
        </xsl:call-template>
        <xsl:call-template name="Opcional">
            <xsl:with-param name="valor" select="./@Unidad"/>
        </xsl:call-template>
        <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@NombreCombustible"/>
        </xsl:call-template>
        <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@FolioOperacion"/>
        </xsl:call-template>
        <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@ValorUnitario"/>
        </xsl:call-template>
        <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@Importe"/>
        </xsl:call-template>

        <!--
            Iniciamos el manejo de los elementos hijo en la secuencia 
        -->
        <xsl:apply-templates select="./ecc12:Traslados"/>
    </xsl:template>

    <!--
       Iniciamos el manejo de los elementos hijo en la secuencia Traslado
    -->
    <xsl:template match="ecc12:Traslado">
        <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@Impuesto"/>
        </xsl:call-template>
        <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@TasaOCuota"/>
        </xsl:call-template>
        <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@Importe"/>
        </xsl:call-template>
    </xsl:template>

</xsl:stylesheet>

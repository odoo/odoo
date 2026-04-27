<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="2.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:fn="http://www.w3.org/2005/xpath-functions" xmlns:gceh="http://www.sat.gob.mx/GastosHidrocarburos10">

  <xsl:template match="gceh:GastosHidrocarburos">
    <!--Manejador de Atributos GastosHidrocarburos-->
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Version" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@NumeroContrato" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@AreaContractual" />
    </xsl:call-template>

    <!--  Iniciamos el manejo de los elementos hijo en la secuencia -->
    <xsl:for-each select="./gceh:Erogacion">
      <xsl:apply-templates select="."/>
    </xsl:for-each>
  </xsl:template>

  <xsl:template match="gceh:Erogacion">
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@TipoErogacion" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@MontocuErogacion" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Porcentaje" />
    </xsl:call-template>

    <!--  Iniciamos el tratamiento de los atributos de gceh:DocumentoRelacionado-->
    <xsl:for-each select="./gceh:DocumentoRelacionado">
      <xsl:apply-templates select="."/>
    </xsl:for-each>
    <xsl:for-each select="./gceh:Actividades">
      <xsl:apply-templates select="."/>
    </xsl:for-each>
    <xsl:for-each select="./gceh:CentroCostos">
      <xsl:apply-templates select="."/>
    </xsl:for-each>
  </xsl:template>

  <!--  Iniciamos el tratamiento de los atributos de gceh:DocumentoRelacionado-->
  <xsl:template match="gceh:DocumentoRelacionado">

    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@OrigenErogacion" />
    </xsl:call-template>

    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@FolioFiscalVinculado" />
    </xsl:call-template>

    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@RFCProveedor" />
    </xsl:call-template>

    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@MontoTotalIVA" />
    </xsl:call-template>

    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@MontoRetencionISR" />
    </xsl:call-template>

    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@MontoRetencionIVA" />
    </xsl:call-template>

    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@MontoRetencionOtrosImpuestos" />
    </xsl:call-template>

    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@NumeroPedimentoVinculado" />
    </xsl:call-template>

    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@ClavePedimentoVinculado" />
    </xsl:call-template>

    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@ClavePagoPedimentoVinculado" />
    </xsl:call-template>

    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@MontoIVAPedimento" />
    </xsl:call-template>

    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@OtrosImpuestosPagadosPedimento" />
    </xsl:call-template>

    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@FechaFolioFiscalVinculado" />
    </xsl:call-template>

    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Mes" />
    </xsl:call-template>

    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@MontoTotalErogaciones" />
    </xsl:call-template>

  </xsl:template>

  <!--  Iniciamos el tratamiento de los atributos de gceh:Actividades-->
  <xsl:template match="gceh:Actividades">
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@ActividadRelacionada" />
    </xsl:call-template>

    <xsl:for-each select="./gceh:SubActividades">
      <xsl:apply-templates select="."/>
    </xsl:for-each>

 </xsl:template>

  <xsl:template match="gceh:SubActividades">
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@SubActividadRelacionada" />
    </xsl:call-template>

    <xsl:for-each select="./gceh:Tareas">
      <xsl:apply-templates select="."/>
    </xsl:for-each>
  </xsl:template>
  
  <xsl:template match="gceh:Tareas">
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@TareaRelacionada" />
    </xsl:call-template>
  </xsl:template>

  <!--  Iniciamos el tratamiento de los atributos de gceh:CentroCostos-->
  <xsl:template match="gceh:CentroCostos">

    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@Campo" />
    </xsl:call-template>

    <xsl:for-each select="./gceh:Yacimientos">
      <xsl:apply-templates select="."/>
    </xsl:for-each>

  </xsl:template>

  <xsl:template match="gceh:Yacimientos">

    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@Yacimiento" />
    </xsl:call-template>

    <xsl:for-each select="./gceh:Pozos">
      <xsl:apply-templates select="."/>
    </xsl:for-each>

  </xsl:template>

  <xsl:template match="gceh:Pozos">

    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@Pozo" />
    </xsl:call-template>
  </xsl:template>


</xsl:stylesheet>
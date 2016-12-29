<?xml version="1.0" ?><xsl:stylesheet version="1.0" xmlns:fn="http://www.w3.org/2005/xpath-functions" xmlns:nomina="http://www.sat.gob.mx/nomina" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output encoding="UTF-8" indent="no" method="text" version="1.0"/>

  <!-- Manejador de nodos tipo nomina -->
  <xsl:template match="nomina:Nomina">

    <!--Iniciamos el tratamiento de los atributos de Nómina -->

    <xsl:choose>
      
      <xsl:when test="./@Version='1.0'">
        
        <xsl:call-template name="Requerido">
          <xsl:with-param name="valor" select="./@Version"/>
        </xsl:call-template>

        <xsl:call-template name="Requerido">
          <xsl:with-param name="valor" select="./@RegistroPatronal"/>
        </xsl:call-template>

        <xsl:call-template name="Requerido">
          <xsl:with-param name="valor" select="./@NumEmpleado"/>
        </xsl:call-template>

        <xsl:call-template name="Requerido">
          <xsl:with-param name="valor" select="./@CURP"/>
        </xsl:call-template>

        <xsl:call-template name="Requerido">
          <xsl:with-param name="valor" select="./@TipoRegimen"/>
        </xsl:call-template>

        <xsl:call-template name="Opcional">
          <xsl:with-param name="valor" select="./@NumSeguridadSocial"/>
        </xsl:call-template>

        <xsl:call-template name="Opcional">
          <xsl:with-param name="valor" select="./@CLABE"/>
        </xsl:call-template>

        <xsl:call-template name="Opcional">
          <xsl:with-param name="valor" select="./@Banco"/>
        </xsl:call-template>

        <!--Iniciamos el tratamiento de los atributos de Ingresos -->

        <xsl:call-template name="Requerido">
          <xsl:with-param name="valor" select="./nomina:Ingresos/@TotalGravado"/>
        </xsl:call-template>

        <xsl:call-template name="Requerido">
          <xsl:with-param name="valor" select="./nomina:Ingresos/@TotalExento"/>
        </xsl:call-template>

        <!--Iniciamos el tratamiento de los atributos de descuentos -->

        <xsl:call-template name="Requerido">
          <xsl:with-param name="valor" select="./nomina:Descuentos/@Total"/>
        </xsl:call-template>
        
      </xsl:when>
      
      <xsl:when test="./@Version='1.1'">

        <xsl:call-template name="Requerido">
          <xsl:with-param name="valor" select="./@Version"/>
        </xsl:call-template>

        <xsl:call-template name="Opcional">
          <xsl:with-param name="valor" select="./@RegistroPatronal"/>
        </xsl:call-template>

        <xsl:call-template name="Requerido">
          <xsl:with-param name="valor" select="./@NumEmpleado"/>
        </xsl:call-template>

        <xsl:call-template name="Requerido">
          <xsl:with-param name="valor" select="./@CURP"/>
        </xsl:call-template>

        <xsl:call-template name="Requerido">
          <xsl:with-param name="valor" select="./@TipoRegimen"/>
        </xsl:call-template>

        <xsl:call-template name="Opcional">
          <xsl:with-param name="valor" select="./@NumSeguridadSocial"/>
        </xsl:call-template>

        <xsl:call-template name="Requerido">
          <xsl:with-param name="valor" select="./@FechaPago"/>
        </xsl:call-template>

        <xsl:call-template name="Requerido">
          <xsl:with-param name="valor" select="./@FechaInicialPago"/>
        </xsl:call-template>

        <xsl:call-template name="Requerido">
          <xsl:with-param name="valor" select="./@FechaFinalPago"/>
        </xsl:call-template>

        <xsl:call-template name="Requerido">
          <xsl:with-param name="valor" select="./@NumDiasPagados"/>
        </xsl:call-template>

        <xsl:call-template name="Opcional">
          <xsl:with-param name="valor" select="./@Departamento"/>
        </xsl:call-template>

        <xsl:call-template name="Opcional">
          <xsl:with-param name="valor" select="./@CLABE"/>
        </xsl:call-template>

        <xsl:call-template name="Opcional">
          <xsl:with-param name="valor" select="./@Banco"/>
        </xsl:call-template>

        <xsl:call-template name="Opcional">
          <xsl:with-param name="valor" select="./@FechaInicioRelLaboral"/>
        </xsl:call-template>

        <xsl:call-template name="Opcional">
          <xsl:with-param name="valor" select="./@Antiguedad"/>
        </xsl:call-template>

        <xsl:call-template name="Opcional">
          <xsl:with-param name="valor" select="./@Puesto"/>
        </xsl:call-template>

        <xsl:call-template name="Opcional">
          <xsl:with-param name="valor" select="./@TipoContrato"/>
        </xsl:call-template>

        <xsl:call-template name="Opcional">
          <xsl:with-param name="valor" select="./@TipoJornada"/>
        </xsl:call-template>

        <xsl:call-template name="Requerido">
          <xsl:with-param name="valor" select="./@PeriodicidadPago"/>
        </xsl:call-template>

        <xsl:call-template name="Opcional">
          <xsl:with-param name="valor" select="./@SalarioBaseCotApor"/>
        </xsl:call-template>

        <xsl:call-template name="Opcional">
          <xsl:with-param name="valor" select="./@RiesgoPuesto"/>
        </xsl:call-template>

        <xsl:call-template name="Opcional">
          <xsl:with-param name="valor" select="./@SalarioDiarioIntegrado"/>
        </xsl:call-template>

        <!--Iniciamos el tratamiento de los elementos de Nómina -->

        <xsl:if test="./nomina:Percepciones">
          <xsl:apply-templates select="./nomina:Percepciones"/>
        </xsl:if>

        <xsl:if test="./nomina:Deducciones">
          <xsl:apply-templates select="./nomina:Deducciones"/>
        </xsl:if>

        <xsl:for-each select="./nomina:Incapacidades">
          <xsl:apply-templates select="."/>
        </xsl:for-each>

        <xsl:for-each select="./nomina:HorasExtras">
          <xsl:apply-templates select="."/>
        </xsl:for-each>

      </xsl:when>
      
    </xsl:choose>

  </xsl:template>

  <xsl:template match="nomina:Percepciones">

    <!--Iniciamos el tratamiento de los atributos de Percepciones -->

    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@TotalGravado"/>
    </xsl:call-template>

    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@TotalExento"/>
    </xsl:call-template>

    <!--Iniciamos el tratamiento del los elementos de Percepciones-->

    <xsl:for-each select="./nomina:Percepcion">
      <xsl:apply-templates select="."/>
    </xsl:for-each>

  </xsl:template>

  <xsl:template match="nomina:Percepcion">

    <!--Iniciamos el tratamiento de los atributos de Percepcion -->

    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@TipoPercepcion"/>
    </xsl:call-template>

    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Clave"/>
    </xsl:call-template>

    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Concepto"/>
    </xsl:call-template>

    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@ImporteGravado"/>
    </xsl:call-template>

    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@ImporteExento"/>
    </xsl:call-template>

  </xsl:template>

  <xsl:template match="nomina:Deducciones">

    <!--Iniciamos el tratamiento de los atributos de Deducciones -->

    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@TotalGravado"/>
    </xsl:call-template>

    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@TotalExento"/>
    </xsl:call-template>

    <!--Iniciamos el tratamiento del los elementos de Deducciones-->

    <xsl:for-each select="./nomina:Deduccion">
      <xsl:apply-templates select="."/>
    </xsl:for-each>

  </xsl:template>

  <xsl:template match="nomina:Deduccion">

    <!--Iniciamos el tratamiento de los atributos de Deduccion -->

    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@TipoDeduccion"/>
    </xsl:call-template>

    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Clave"/>
    </xsl:call-template>

    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Concepto"/>
    </xsl:call-template>

    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@ImporteGravado"/>
    </xsl:call-template>

    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@ImporteExento"/>
    </xsl:call-template>

  </xsl:template>

  <xsl:template match="nomina:Incapacidades">

    <!--Iniciamos el tratamiento del los elementos de Incapacidades-->

    <xsl:for-each select="./nomina:Incapacidad">
      <xsl:apply-templates select="."/>
    </xsl:for-each>

  </xsl:template>

  <xsl:template match="nomina:Incapacidad">

    <!--Iniciamos el tratamiento de los atributos de Incapacidad -->

    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@DiasIncapacidad"/>
    </xsl:call-template>

    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@TipoIncapacidad"/>
    </xsl:call-template>

    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Descuento"/>
    </xsl:call-template>
  </xsl:template>

    <xsl:template match="nomina:HorasExtras">

    <!--Iniciamos el tratamiento del los elementos de HorasExtras-->

    <xsl:for-each select="./nomina:HorasExtra">
      <xsl:apply-templates select="."/>
    </xsl:for-each>

  </xsl:template>

  <xsl:template match="nomina:HorasExtra">

    <!--Iniciamos el tratamiento de los atributos de HorasExtra -->
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Dias"/>
    </xsl:call-template>

    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@TipoHoras"/>
    </xsl:call-template>

    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@HorasExtra"/>
    </xsl:call-template>

    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@ImportePagado"/>
    </xsl:call-template>
  </xsl:template>

</xsl:stylesheet>
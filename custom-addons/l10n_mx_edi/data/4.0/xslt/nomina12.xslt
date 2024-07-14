<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="2.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:fn="http://www.w3.org/2005/xpath-functions" xmlns:nomina12="http://www.sat.gob.mx/nomina12">

  <xsl:template match="nomina12:Nomina">
    <!--Manejador de nodos tipo Nomina-->
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Version" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@TipoNomina" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@FechaPago" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@FechaInicialPago" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@FechaFinalPago" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@NumDiasPagados" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@TotalPercepciones" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@TotalDeducciones" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@TotalOtrosPagos" />
    </xsl:call-template>

    <!--  Iniciamos el manejo de los elementos hijo en la secuencia -->
    <xsl:for-each select="./nomina12:Emisor">
      <xsl:apply-templates select="."/>
    </xsl:for-each>

    <xsl:for-each select="./nomina12:Receptor">
      <xsl:apply-templates select="."/>
    </xsl:for-each>

    <xsl:for-each select="./nomina12:Percepciones">
      <xsl:apply-templates select="."/>
    </xsl:for-each>

    <xsl:for-each select="./nomina12:Deducciones">
      <xsl:apply-templates select="."/>
    </xsl:for-each>

    <xsl:for-each select="./nomina12:OtrosPagos">
      <xsl:apply-templates select="."/>
    </xsl:for-each>

    <xsl:for-each select="./nomina12:Incapacidades">
      <xsl:apply-templates select="."/>
    </xsl:for-each>

  </xsl:template>

  <xsl:template match="nomina12:Emisor">
    <!--Manejador de nodos tipo nomina12:Emisor-->
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@Curp" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@RegistroPatronal" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@RfcPatronOrigen" />
    </xsl:call-template>

    <!--  Iniciamos el tratamiento de los atributos de nomina12:EntidadSNCF-->
    <xsl:for-each select="./nomina12:EntidadSNCF">
      <xsl:apply-templates select="."/>
    </xsl:for-each>

  </xsl:template>

    <!--  Iniciamos el manejo de los elementos hijo en la secuencia EntidadSNCF-->
  <xsl:template match="nomina12:EntidadSNCF">
    <!--  Iniciamos el manejo de los nodos dependientes -->
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@OrigenRecurso" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@MontoRecursoPropio" />
    </xsl:call-template>

  </xsl:template>

  <xsl:template match="nomina12:Receptor">
    <!--Manejador de nodos tipo nomina12:Receptor-->
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Curp" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@NumSeguridadSocial" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@FechaInicioRelLaboral" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@Antigüedad" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@TipoContrato" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@Sindicalizado" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@TipoJornada" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@TipoRegimen" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@NumEmpleado" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@Departamento" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@Puesto" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@RiesgoPuesto" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@PeriodicidadPago" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@Banco" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@CuentaBancaria" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@SalarioBaseCotApor" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@SalarioDiarioIntegrado" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@ClaveEntFed" />
    </xsl:call-template>

    <!--  Iniciamos el tratamiento de los atributos de nomina12:SubContratacion-->
    <xsl:for-each select="./nomina12:SubContratacion">
      <xsl:apply-templates select="."/>
    </xsl:for-each>

  </xsl:template>

    <!--  Iniciamos el manejo de los elementos hijo en la secuencia SubContratacion-->
  <xsl:template match="nomina12:SubContratacion">
    <!--  Iniciamos el manejo de los nodos dependientes -->
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@RfcLabora" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@PorcentajeTiempo" />
    </xsl:call-template>

  </xsl:template>

  <xsl:template match="nomina12:Percepciones">
    <!--Manejador de nodos tipo nomina12:Percepciones-->
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@TotalSueldos" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@TotalSeparacionIndemnizacion" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@TotalJubilacionPensionRetiro" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@TotalGravado" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@TotalExento" />
    </xsl:call-template>

    <!--  Iniciamos el tratamiento de los atributos de nomina12:Percepcion-->
    <xsl:for-each select="./nomina12:Percepcion">
      <xsl:apply-templates select="."/>
    </xsl:for-each>

    <!--  Iniciamos el tratamiento de los atributos de nomina12:JubilacionPensionRetiro-->
    <xsl:for-each select="./nomina12:JubilacionPensionRetiro">
      <xsl:apply-templates select="."/>
    </xsl:for-each>

    <!--  Iniciamos el tratamiento de los atributos de nomina12:SeparacionIndemnizacion-->
    <xsl:for-each select="./nomina12:SeparacionIndemnizacion">
      <xsl:apply-templates select="."/>
    </xsl:for-each>

  </xsl:template>
   <!--  Iniciamos el manejo de los elementos hijo en la secuencia Percepcion-->
  <xsl:template match="nomina12:Percepcion">
    <!--Manejador de nodos tipo nomina12:Percepcion-->
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@TipoPercepcion" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Clave" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Concepto" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@ImporteGravado" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@ImporteExento" />
    </xsl:call-template>

    <!--  Iniciamos el tratamiento de los atributos de nomina12:AccionesOTitulos-->
    <xsl:for-each select="./nomina12:AccionesOTitulos">
      <xsl:apply-templates select="."/>
    </xsl:for-each>
    <!--  Iniciamos el tratamiento de los atributos de nomina12:HorasExtra-->
    <xsl:for-each select="./nomina12:HorasExtra">
      <xsl:apply-templates select="."/>
    </xsl:for-each>

  </xsl:template>

  <!--  Iniciamos el manejo de los elementos hijo en la secuencia AccionesOTitulos-->
  <xsl:template match="nomina12:AccionesOTitulos">
    <!--  Iniciamos el manejo de los nodos dependientes -->
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@ValorMercado" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@PrecioAlOtorgarse" />
    </xsl:call-template>
  </xsl:template>

  <!--  Iniciamos el manejo de los elementos hijo en la secuencia HorasExtra-->
  <xsl:template match="nomina12:HorasExtra">
    <!--  Iniciamos el manejo de los nodos dependientes -->
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Dias" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@TipoHoras" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@HorasExtra" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@ImportePagado" />
    </xsl:call-template>
  </xsl:template>

   <!--  Iniciamos el manejo de los elementos hijo en la secuencia JubilacionPensionRetiro-->
  <xsl:template match="nomina12:JubilacionPensionRetiro">
    <!--Manejador de nodos tipo nomina12:JubilacionPensionRetiro-->
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@TotalUnaExhibicion" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@TotalParcialidad" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@MontoDiario" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@IngresoAcumulable" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@IngresoNoAcumulable" />
    </xsl:call-template>
  </xsl:template>

    <!--  Iniciamos el manejo de los elementos hijo en la secuencia SeparacionIndemnizacion-->
  <xsl:template match="nomina12:SeparacionIndemnizacion">
    <!--Manejador de nodos tipo nomina12:JubilacionPensionRetiro-->
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@TotalPagado" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@NumAñosServicio" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@UltimoSueldoMensOrd" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@IngresoAcumulable" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@IngresoNoAcumulable" />
    </xsl:call-template>
  </xsl:template>

  <xsl:template match="nomina12:Deducciones">
    <!--Manejador de nodos tipo nomina12:Deducciones-->
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@TotalOtrasDeducciones" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@TotalImpuestosRetenidos" />
    </xsl:call-template>

    <!--  Iniciamos el tratamiento de los atributos de nomina12:Deduccion-->
    <xsl:for-each select="./nomina12:Deduccion">
      <xsl:apply-templates select="."/>
    </xsl:for-each>

  </xsl:template>

    <!--  Iniciamos el manejo de los elementos hijo en la secuencia Deduccion-->
  <xsl:template match="nomina12:Deduccion">
    <!--Manejador de nodos tipo nomina12:Deduccion-->
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@TipoDeduccion" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Clave" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Concepto" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Importe" />
    </xsl:call-template>
  </xsl:template>

    <xsl:template match="nomina12:OtrosPagos">

    <!--  Iniciamos el tratamiento de los atributos de nomina12:OtroPago-->
    <xsl:for-each select="./nomina12:OtroPago">
      <xsl:apply-templates select="."/>
    </xsl:for-each>

  </xsl:template>
  
  <!--  Iniciamos el manejo de los elementos hijo en la secuencia OtroPago-->
  <xsl:template match="nomina12:OtroPago">
    <!--Manejador de nodos tipo nomina12:OtroPago-->
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@TipoOtroPago" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Clave" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Concepto" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Importe" />
    </xsl:call-template>

    <!--  Iniciamos el tratamiento de los atributos de nomina12:SubsidioAlEmpleo-->
    <xsl:for-each select="./nomina12:SubsidioAlEmpleo">
      <xsl:apply-templates select="."/>
    </xsl:for-each>
    <!--  Iniciamos el tratamiento de los atributos de nomina12:CompensacionSaldosAFavor-->
    <xsl:for-each select="./nomina12:CompensacionSaldosAFavor">
      <xsl:apply-templates select="."/>
    </xsl:for-each>

  </xsl:template>

  <!--  Iniciamos el manejo de los elementos hijo en la secuencia SubsidioAlEmpleo-->
  <xsl:template match="nomina12:SubsidioAlEmpleo">
    <!--Manejador de nodos tipo nomina12:SubsidioAlEmpleo-->
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@SubsidioCausado" />
    </xsl:call-template>
  </xsl:template>

  <!--  Iniciamos el manejo de los elementos hijo en la secuencia CompensacionSaldosAFavor-->
  <xsl:template match="nomina12:CompensacionSaldosAFavor">
    <!--Manejador de nodos tipo nomina12:CompensacionSaldosAFavor-->
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@SaldoAFavor" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Año" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@RemanenteSalFav" />
    </xsl:call-template>
  </xsl:template>

  <xsl:template match="nomina12:Incapacidades">
    <!--  Iniciamos el tratamiento de los atributos de nomina12:Incapacidades-->
    <xsl:for-each select="./nomina12:Incapacidad">
      <xsl:apply-templates select="."/>
    </xsl:for-each>
  </xsl:template>

  <!--  Iniciamos el manejo de los elementos hijo en la secuencia Incapacidad-->
  <xsl:template match="nomina12:Incapacidad">
    <!--Manejador de nodos tipo nomina12:Incapacidad-->
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@DiasIncapacidad" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@TipoIncapacidad" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@ImporteMonetario" />
    </xsl:call-template>

  </xsl:template>
</xsl:stylesheet>

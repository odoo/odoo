# -*- coding: utf-8 -*-


class amount_to_text:
    """
    Transforma de una cantidad numerica a cantidad en letra
    ej. 200 -> doscientos
    """

    def __init__(self):
        self._n1 = [
            "un", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho",
            "nueve", "diez", "once", "doce", "trece", "catorce", "quince",
            "dieciseis", "diecisiete", "dieciocho", "diecinueve", "veinte"]

        self._n11 = ["un", "dos", "tres", "cuatro",
                     "cinco", "seis", "siete", "ocho", "nueve"]

        self._n2 = [
            "dieci", "veinti", "treinta", "cuarenta", "cincuenta", "sesenta",
            "setenta", "ochenta", "noventa"]

        self._n3 = ["ciento", "dosc", "tresc", "cuatroc", "quin", "seisc",
                    "setec", "ochoc", "novec"]

    def amount_to_text_cheque(self, nNumero, intermedio="pesos ", sufijo="M. N."):
        """
        @params nNumero : Amount for convert to text
        @params intermedio : Name Divisa
        @sufijo : Sufix of the currency
        """
        nNumero = round(nNumero, 2)
        strCantEntera = self.amount_to_text(nNumero)
        intCantDecimal = self.extraeDecimales(nNumero)
        if intCantDecimal <= 9:
            strCantDecimal = "0%d" % (intCantDecimal)
        else:
            strCantDecimal = "%d" % (intCantDecimal)
        strCantDecimal += "/100"
        return strCantEntera+' '+intermedio+' '+strCantDecimal+' '+sufijo

    def extraeDecimales(self, nNumero, max_digits=2):
        """
        @params nNumero : Number complete whit decimals
        @params max_digits : Maximum number of decimals to take
        """
        strDecimales = str(round(nNumero % 1, 2)).replace('0.', '')
        strDecimales += "0"*max_digits
        strDecimales = strDecimales[0:max_digits]
        return int(strDecimales)

    def amount_to_text(self, nNumero, lFemenino=False):
        """
        NOTE: Only numbers integer, omittes the DECIMALS
        amount_to_text(nNumero, lFemenino) --> cLiteral
            Converts the number to string literal of characters
            example:  201   --> "Two thousand one"
                      1111  --> "One thousand one hundred eleven"
        @params nNumero : Number to conert
        @params lFemenino : 'true' if the literal is female
        """
        # Nos aseguramos del tipo de <nNumero>
        # se podria adaptar para usar otros tipos (pe: float)
        nNumero = int(nNumero)
        if nNumero < 0:
            cRes = "menos "+self._amount_to_text(-nNumero, lFemenino)
        elif nNumero == 0:
            cRes = "cero"
        else:
            cRes = self._amount_to_text(nNumero, lFemenino)

        # Excepciones a considerar
        if not lFemenino and nNumero % 10 == 1 and nNumero % 100 != 11:
            cRes += "o"
        # cRes = cRes.upper()
        # cRes = cRes.capitalize()
        return cRes

    # Funcion auxiliar recursiva
    def _amount_to_text(self, n, lFemenino=0):
        """
        @params nNumero : Number to conert
        @params lFemenino : '0' if the literal isn't female
        """

        # Localizar los billones
        prim, resto = divmod(n, 10**12)
        if prim != 0:
            if prim == 1:
                cRes = "un billon"
            else:
                cRes = self._amount_to_text(
                    prim, 0)+" billones"  # Billones es masculino

            if resto != 0:
                cRes += " "+self._amount_to_text(resto, lFemenino)

        else:
        # Localizar millones
            prim, resto = divmod(n, 10**6)
            if prim != 0:
                if prim == 1:
                    cRes = "un millon"
                else:
                    cRes = self._amount_to_text(
                        prim, 0)+" millones"  # Millones es masculino

                if resto != 0:
                    cRes += " " + self._amount_to_text(resto, lFemenino)

            else:
            # Localizar los miles
                prim, resto = divmod(n, 10**3)
                if prim != 0:
                    if prim == 1:
                        cRes = "un mil"
                    else:
                        cRes = self._amount_to_text(prim, lFemenino)+" mil"

                    if resto != 0:
                        cRes += " " + self._amount_to_text(resto, lFemenino)

                else:
                # Localizar los cientos
                    prim, resto = divmod(n, 100)
                    prim = int(prim)
                    if prim != 0:
                        if prim == 1:
                            if resto == 0:
                                cRes = "cien"
                            else:
                                cRes = "ciento"
                        else:
                            cRes = self._n3[prim-1]
                            if lFemenino:
                                cRes += "ientas"
                            else:
                                cRes += "ientos"

                        if resto != 0:
                            cRes += " "+self._amount_to_text(resto, lFemenino)

                    else:
                    # Localizar las decenas
                        if lFemenino and n == 1:
                            cRes = "una"
                        elif n <= 20:
                            cRes = self._n1[n-1]
                        else:
                            prim, resto = divmod(n, 10)
                            prim = int(prim)
                            resto = int(resto)
                            cRes = self._n2[prim-1]
                            if resto != 0:
                                if prim == 2:
                                    cRes += self._n11[resto-1]
                                else:
                                    cRes += " y "+self._n1[resto-1]

                                if lFemenino and resto == 1:
                                    cRes += "a"
        return cRes


def get_amount_to_text(self, amount, lang, currency=""):
    """
    @params amount : Amount for convert to text
    @params lang  : Language to used for the text converted
    @params currency : Name of currency used in amount
    """
    if currency.upper() in ('MXP', 'MXN', 'PESOS', 'PESOS MEXICANOS'):
        sufijo = 'M. N.'
        currency = 'PESOS'
    elif currency.upper() in ('USD'):
        sufijo = 'USD'
        currency = 'DÓLARES'
    elif currency.upper() in ('EUR'):
        sufijo = 'EUR'
        currency = 'EUROS'		
    elif currency.upper() in ('CAD'):
        sufijo = 'CAD'
        currency = 'DÓLARES'
    else:
        sufijo = 'M. E.'
    # return amount_to_text(amount, lang, currency)
    amount_text = amount_to_text().amount_to_text_cheque(
        amount, currency, sufijo)
    amount_text = amount_text and amount_text.upper() or ''
    return amount_text

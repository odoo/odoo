/*
Copyright (c) 2008-2012 NaN Projectes de Programari Lliure, S.L.
                        http://www.NaN-tic.com

WARNING: This program as such is intended to be used by professional
programmers who take the whole responsability of assessing all potential
consequences resulting from its eventual inadequacies and bugs
End users who are looking for a ready-to-use solution with commercial
garantees and support are strongly adviced to contract a Free Software
Service Company

This program is Free Software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
*/
package com.nantic.jasperreports;

import net.sf.jasperreports.engine.JRRewindableDataSource;
import net.sf.jasperreports.engine.JRException;
import net.sf.jasperreports.engine.data.JRCsvDataSource;
import net.sf.jasperreports.engine.JRField;
import net.sf.jasperreports.engine.data.JRXmlDataSource;
import net.sf.jasperreports.engine.design.JRDesignField;

import java.io.*;
import java.text.NumberFormat;
import java.text.SimpleDateFormat;
import java.util.Locale;


/*
This class overrides getFieldValue() from JRXmlDataSource to parse
java.lang.Object fields that will come from Python coded with data
for each language.
*/
public class XmlMultiLanguageDataSource extends JRXmlDataSource {
    public XmlMultiLanguageDataSource(String uri, String selectExpression) throws JRException {
        super(uri, selectExpression);
    }

    public Object getFieldValue(JRField jrField) throws JRException {
        Object value;
        if ( jrField.getValueClassName().equals( "java.lang.Object" ) ) {
            JRDesignField fakeField = new JRDesignField();
            fakeField.setName( jrField.getName() );
            fakeField.setDescription( jrField.getDescription() );
            fakeField.setValueClassName( "java.lang.String" );
            fakeField.setValueClass( String.class );
            value = super.getFieldValue( fakeField );

            LanguageTable values = new LanguageTable("en_US");
            String v = (String) value;
            String[] p = v.split( "\\|" );
            for( int j=0; j < p.length ; j++ ) {
                //System.out.println( p[j] );
                String[] map = p[j].split( "~" );
                if ( map.length == 2 ) 
                    values.put( map[0], map[1] );
            }
            value = (Object)values;
        } else {
            value = super.getFieldValue(jrField);
        }
        return value;
    }
}



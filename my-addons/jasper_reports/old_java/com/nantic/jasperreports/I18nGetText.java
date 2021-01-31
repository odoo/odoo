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

import java.util.Iterator;
import java.util.ArrayList;

import java.io.PrintStream;
import net.sf.jasperreports.engine.JasperCompileManager;

public class I18nGetText {
    public static void main (String [] args) {
        if ( args.length != 1 ) {
            System.out.println( "Syntax: I18nGetText filename.jrxml" );
            System.exit(1);
        }
        String fileName = args[0];

        System.setProperty("jasper.reports.compiler.class", "com.nantic.jasperreports.I18nGroovyCompiler");

        try {
            I18nGroovyCompiler.sourceCodeList = new ArrayList();
            JasperCompileManager.compileReport( fileName );
            //System.out.println( I18nGroovyCompiler.lastGeneratedSourceCode );
            PrintStream out = new PrintStream(System.out, true, "UTF-8");
            Iterator<String> iterator = I18nGroovyCompiler.sourceCodeList.iterator();
            while ( iterator.hasNext() ) {
                out.println( iterator.next() );
            }
            System.exit(0);

        } catch (Exception e) {
            System.out.println( "Error compiling report: " + e.getMessage() );
            System.exit(2);
        }
    }
}

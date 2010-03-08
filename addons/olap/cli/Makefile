DATABASE = 'bi'

all: simple sale date where sublevels calc_meas cross page complex test

simple:
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "tinyerp" -c "select {[User].[all]} on rows, {[measures].[Credit Limit],[measures].[Count]} on columns from Partner"
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "tinyerp" -c "select {[measures].[Credit Limit],[measures].[Count]} on rows, {[User].[all],[User].children} on columns from Partner"
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "tinyerp" -c "select {[User].children} on rows from Partner"
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "tinyerp" -c "select {[User].[all],[User].children} on rows, {[measures].[Credit Limit],[measures].[Count]} on columns from Partner"
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "tinyerp" -c "select {[User].children} on rows, {[User].children} on columns from Partner where ([measures].[Count])"
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "tinyerp" -c "select {[User].children} on rows, {[measures].[Count]} on columns from Partner where ([User].[3])" 
#	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "tinyerp" -c "select {[Date].[2008]} on rows, {[measures].[Credit Limit],[measures].[Count]} on columns from Partner"
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "tinyerp" -c "select {[Date].[all],[Date].children} on rows, {[measures].[Credit Limit],[measures].[Count]} on columns from Partner"

sale:
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "OpenERPSales" -c "select {[Partner Country].children} on rows from Sales"
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "OpenERPSales" -c "select {[City].children} on rows from Sales"
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "OpenERPSales" -c "select {[City].children,[City].[Paris].children,[Partner Country].children} on rows, {[measures].[Total Sales]} on columns from Sales"

	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "OpenERPSales" -c "select {[Order Date].[all],[Order Date].children,[Users].children} on rows, {[measures].[Average Sales],[measures].[Total Sales]} on columns from Sales"
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "OpenERPSales" -c "select {[Order Date].children, [Order Date].[all]} on rows, {[measures].[Average Sales],[measures].[Total Sales]} on columns from Sales"

	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "OpenERPSales" -c "select {[Partner Country].children} on rows, {[measures].[Average Sales],[measures].[Total Sales]} on columns from Sales"
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "OpenERPSales" -c "select {[Partner Country].[China]} on rows, {[measures].[Average Sales],[measures].[Total Sales]} on columns from Sales"
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "OpenERPSales" -c "select {[Partner Country].[Belgium]} on rows, {[measures].[Average Sales],[measures].[Total Sales]} on columns from Sales"

date:
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "OpenERPSales" -c "select {[Order Date].children} on rows, {[measures].[Average Sales],[measures].[Total Sales]} on columns from Sales"
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "OpenERPSales" -c "select {[Order Date].[2007]} on rows, {[measures].[Average Sales],[measures].[Total Sales]} on columns from Sales"
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "OpenERPSales" -c "select {[Order Date].[2008]} on rows, {[measures].[Average Sales],[measures].[Total Sales]} on columns from Sales"
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "OpenERPSales" -c "select {[Order Date].children,[Order Date].[2008].children,[Order Date].[2008].[Q2].children} on rows, {[measures].[Total Sales]} on columns from Sales"
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "OpenERPSales" -c "select {[Order Date].children,[Order Date].[2008].children,[Order Date].[2008].[Q2].children} on rows, {[measures].[Total Sales]} on columns from Sales where ([Order Date].[2008].[Q2])"

where:
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "OpenERPSales" -c " select crossjoin (crossjoin ({[Order Date].[all],[Users].[all]} , {[Users].children} ) , {[Partner Country].[all]}) on rows, {[measures].[Units Sold]} on columns from Sales"
sublevels:
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "OpenERPSales" -c "select {[City].[all],[City].children} on rows, {[measures].[Total Sales]} on columns from Sales"
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "OpenERPSales" -c "select {[City].[all],[City].children} on rows, {[measures].[Total Sales]} on columns from Sales"
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "OpenERPSales" -c "select {[City].[all],[City].children,[City].[Liege].children} on rows, {[measures].[Total Sales]} on columns from Sales"
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "OpenERPSales" -c "select {[Products Category].[all],[Products Category].children} on rows, {[measures].[Total Sales]} on columns from Sales"
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "OpenERPSales" -c "select {[Products Category].[all],[Products Category].children,[Products Category].[PC].children} on rows, {[measures].[Total Sales]} on columns from Sales"

calc_meas:
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "OpenERPSales" -c "select {[City].[all]} on rows, {[measures].[Total Sales]} on columns from Sales"
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "OpenERPSales" -c "select {[City].[all],[City].children} on rows, {[measures].[Total Sales]} on columns from Sales"
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "OpenERPSales" -c "select {[City].[all],[City].children} on rows, {[measures].[Units Sold],[measures].[Total Sales]} on columns from Sales"

cross:	
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "OpenERPSales" -c "select  crossjoin ({[Order Date].[all],[Order Date].children} , {[All Products].[all]}) on rows from Sales"
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "OpenERPSales" -c "select crossjoin({[City].[all]},{[Users].[all]}) on rows, {[measures].[Total Sales]} on columns from Sales"
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "OpenERPSales" -c "select crossjoin({[City].[all],[Users].[all]},{[Order Date].[all]}) on rows, {[measures].[Total Sales]} on columns from Sales"
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "OpenERPSales" -c "select crossjoin({[City].[all],[City].children},{[Order Date].children}) on rows, {[measures].[Total Sales]} on columns from Sales"
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "OpenERPSales" -c "select crossjoin(crossjoin({[City].[all],[City].children},{[Users].children}),{[Order Date].children}) on rows, {[measures].[Total Sales]} on columns from Sales"
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "OpenERPSales" -c "select crossjoin(crossjoin({[City].[all],[City].children},{[Users].children}),{[Order Date].children}) on rows, {[measures].[Total Sales],[measures].[Units Sold]} on columns from Sales"
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "OpenERPSales" -c "select crossjoin(crossjoin({[City].[all],[Users].[all]},{[Order Date].[all]}),{[Order Date].children}) on rows, crossjoin({[All Products].[all],[Products Category].[all]},{[Partner Country].children}) on columns from Sales"
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "OpenERPSales" -c "select crossjoin({[City].[all]},{[Users].[all]}) on rows, crossjoin({[measures].[Total Sales]},{[Order Date].children}) on columns from Sales"
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "OpenERPSales" -c "select crossjoin({[City].[all]},{[Users].[all]}) on rows, crossjoin(crossjoin({[measures].[Total Sales]},{[Order Date].children}),{[Users].children}) on columns from Sales"

page:
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "OpenERPSales" -c "select {[City].[all],[City].children} on rows, {[measures].[Units Sold],[measures].[Total Sales]} on columns, {[Order Date].children} on pages from Sales" 
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "OpenERPSales" -c "select {[measures].[Units Sold],[measures].[Total Sales]} on rows, {[City].[all],[City].children} on columns, {[Order Date].children} on pages from Sales"

complex:
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "OpenERPSales" -c "select crossjoin({[City].[all],[City].children},{[Order Date].[all]}) on rows, {[measures].[Units Sold],[measures].[Total Sales]} on columns, {[Order Date].children} on pages from Sales"
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "OpenERPSales" -c "select crossjoin(crossjoin({[City].[all],[City].children},{[Order Date].children}),{[Users].children}) on rows, {[measures].[Units Sold],[measures].[Total Sales]} on columns, {[Order Date].children} on pages from Sales"
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "OpenERPSales" -c "select crossjoin(crossjoin({[City].[all],[City].children},{[Order Date].children}),{[Users].children}) on rows, crossjoin({[measures].[Units Sold],[measures].[Total Sales]},{[City].children}) on columns, {[Order Date].children} on pages from Sales"

test:
	./tinybi.py -d ${DATABASE} -H localhost -U admin -W admin -p 8069 -s "tinyerp" -c " select crossjoin (crossjoin ({[Order Date].[all],[Users].[all]} , {[Users].children} ) , {[Partner Country].[all]}) on rows, {[measures].[Units Sold]} on columns from Sales"
> #### Quantity field is ignored in a sale order
>______
> ***Impacted versions:***
> 
>  - 7.0 and above
> 
> ***Steps to reproduce:***
> 
>  1. create a new sale order
>  2. add a line with product 'Service', quantity 2, unit price 10.0
>  3. validate the sale order
> 
> ***Current behavior:***
> 
>  - Total price of 10.0
> 
> ***Expected behavior:***
> 
>  - Total price of 20.0 (2 * 10 = 20)

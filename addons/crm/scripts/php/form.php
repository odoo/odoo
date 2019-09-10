<html>
<head>
<title>Contact form</title>
</head>
<body>
    <h4>Contact Form</h4>
    <form method="post" action="crmlead.php">
        <label for="firstname">Firstname</label>
            <input type="text" name="name" value="" id="firstname" class="required text" title="Please, fill in your firstname" data-required="true"><br />
        <label for="company">Company</label>
            <input type="text" name="company" value="" id="company" class="required text" title="Please, fill in your company name" data-required="true"><br />
        <label for="jobtitle">Jobtitle</label>
            <input type="text" name="jobtitle" value="" id="jobtitle" class="required text" title="Please, fill in your job title" data-required="true"><br />
        <label for="email">Email</label>
            <input type="text" name="email" value="" id="email" class="required email text" title="Please, enter a valid email address" data-required="true"><br />
        <label for="phone">Phone</label>
            <input type="text" name="phone" value="" id="phone" class="required phone text" title="Please use international format (eg: +32...)" data-required="true">
            
        <label for="city">City</label>
            <input type="text" name="city" value="" id="city" class="required text" title="Please, fill in your city" data-required="true"><br />
        <label for="zip">Zipcode</label>
            <td><input type="text" name="zip" value="" id="zip" class="required text" title="Please, fill in your zipcode" data-required="true"><br />
        <label for="state">State</label><input type="text" name="state" value="" id="state" class="text" title="Please, fill in your state"> <br />
        <label> Country : <?php include('countrylist.php'); ?></label> <br />
        <label for="employees">No.of employees</label>
        
                <select class="required" name="employees" title="Please, select the No. of employees" data-required="true">
                    <option value=""> -- select an option -- </option>
                    <option value="1-5">1-5</option>
                    <option value="5-10">5-10</option>
                    <option value="10-20">10-20</option>

                    <option value="20-100">20-100</option>
                    <option value="100-500">100-500</option>
                    <option value="500+">500+</option>
                </select><br />
                
              <label for="industry">Industry expertise</label>
                <select class="required select" name="industry" title="Please, select an industry" data-required="true">
                    <option value=""> -- select an option -- </option>
                    <option value="auction">Auction Houses</option>
                    <option value="bank">Bank</option>
                    <option value="distribution">Distribution</option>
                    <option value="education">Education</option>

                    <option value="entertainment">Entertainment</option>
                    <option value="erp_integrator">ERP Integrator</option>
                    <option value="food_industries">Food industries</option>
                    <option value="hotels_restaurants">Hotels &amp; restaurants</option>
                    <option value="insurance">Insurance</option>
                    <option value="manufacturing">Manufacturing</option>
                    <option value="non_profit">Non-Profit</option>
                    <option value="public">Public</option>

                    <option value="services">Services</option>
                    <option value="telecommunication">Telecommunication</option>
                    <option value="others">Others</option>
                </select><br />
        <p>
            <label> About : <textarea name="about"></textarea></textarea></label>
        </p>
        <p>
            <input type="submit" value="Send"/> <input type="reset" />
        </p>
    </form>

</body>
</html>



       
        
        

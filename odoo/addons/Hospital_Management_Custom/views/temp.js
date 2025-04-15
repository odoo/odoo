import { useState } from "react";
import Layout from "../components/Layout";
import Head from "next/head";

export default function About() {
  // Separate states for each section
  const [showChatbotContent, setShowChatbotContent] = useState(false);
  const [showMachineLearningContent, setShowMachineLearningContent] = useState(false);
  const [showWebScrapingContent, setShowWebScrapingContent] = useState(false);
  const [showDataScienceContent, setShowDataScienceContent] = useState(false);
  const [showPythonAutomationContent, setShowPythonAutomationContent] = useState(false);
  const [showDataAnalysisContent, setshowDataAnalysisContent]=useState(false)
  const [showApiIntegration, setshowApiIntegration]= useState(false)

  return (
    <Layout>
      <Head>
        <title>About Sajjad Ali Noor | Python Developer & AI Enthusiast</title>
        <meta
          name="description"
          content="Learn about Sajjad Ali Noor, a passionate Python developer and AI enthusiast with expertise in automation, data science, and AI."
        />
        <meta
          name="keywords"
          content="Python developer, AI enthusiast, automation, data science, machine learning, AI chatbot development, web scraping"
        />
        <meta name="author" content="Sajjad Ali Noor" />
        <meta property="og:title" content="About Sajjad Ali Noor | Python Developer & AI Enthusiast" />
        <meta
          property="og:description"
          content="Discover the projects and expertise of Sajjad Ali Noor, specializing in Python automation, AI, data science, and machine learning."
        />
      </Head>

      <div
        style={{
          background: "white",
          minHeight: "100vh",
        }}
      >
        <div className="container mt-4">
          <h1>Sajjad Ali Noor – Passionate Python Developer & AI Solutions Provider</h1>
          <p>
            <strong>Hi, I'm Sajjad Ali Noor!</strong> A passionate Python developer and AI enthusiast. Throughout my career, I have developed expertise in areas such as automation, data science, and AI. Below, you can explore a collection of my best work that showcases the skills I've gained through completing projects from books like *Automate the Boring Stuff with Python* and *Master Python for Data Science*.
          </p>
          <h2
            style={{ cursor: "pointer", display: "flex", alignItems: "center" }}
            onClick={() => setShowStudentApps(!showStudentApps)}
          >
            Some Useful Apps for Students
            <a
              href="#"
              onClick={(e) => e.preventDefault()}
              style={{ marginLeft: "8px", color: "blue" }}
            >
              {showStudentApps ? "-" : "+"}
            </a>
          </h2>
          
          {showStudentApps && (
            <p style={{ backgroundColor: "white", padding: "10px", marginBottom: "10px" }}>
              Whether you're organizing assignments, converting images into notes, or managing reading material, these tools can be incredibly helpful for students. For instance, if you need to **convert scanned handwritten notes or textbook pages into text**, the 
              <a
                href="/dashboard/ImageToText"
                title="Image to Text Converter"
                style={{ color: "blue", textDecoration: "underline", margin: "0 5px" }}
              >
                Image to Text Converter
              </a> 
              makes this task seamless. Similarly, if you want to **share a direct link to your PDF notes with friends or teachers**, the 
              <a
                href="/dashboard/PDF_URL"
                title="Get a PDF URL"
                style={{ color: "blue", textDecoration: "underline", margin: "0 5px" }}
              >
                PDF URL Generator
              </a> 
              can help you create a shareable link instantly. And when your lecture slides are too long or include unnecessary pages, you can quickly tidy them up using the 
              <a
                href="/dashboard/PDF_TRIM"
                title="Trim your PDF"
                style={{ color: "blue", textDecoration: "underline", margin: "0 5px" }}
              >
                PDF Trimming Tool
              </a>. These apps simplify common academic tasks, helping you stay focused and efficient.
            </p>
          )}
         
          
        
          <h2
            style={{ cursor: "pointer", display: "flex", alignItems: "center" }}
            onClick={() => setShowChatbotContent(!showChatbotContent)}
          >
            Chatbot Development & AI Projects
            <a
              href="#"
              onClick={(e) => e.preventDefault()}
              style={{ marginLeft: "8px", color: "blue" }}
            >
              {showChatbotContent ? "-" : "+"}
            </a>
          </h2>
          {showChatbotContent && (
            <p style={{ backgroundColor: "white !important", padding: "10px", marginBottom: "10px" }}>
              <strong>AI-Powered PDF Query Chatbot:</strong> This intelligent chatbot processes PDFs, learns from their content, and provides AI-driven answers using OpenAI’s NLP models. A key highlight of my AI projects, the <a href="https://github.com/Sajjad5037/Pdf-Query-Chatbot" target="_blank" title="AI-Powered PDF Query Chatbot - Smart Document Search and Analysis">PDF Query Chatbot</a> transforms static documents into an interactive knowledge base, making research, business, and legal workflows seamless and efficient.
            </p>
          )}
          
          <h2
            style={{ cursor: "pointer", display: "flex", alignItems: "center" }}
            onClick={() => setshowApiIntegration(!showApiIntegration)}
          >
            API Integration Projects
            <a
              href="#"
              onClick={(e) => e.preventDefault()}
              style={{ marginLeft: "8px", color: "blue" }}
            >
              {showApiIntegration ? "-" : "+"}
            </a>
          </h2>
          {showApiIntegration && (
            <>
              <p>
                One of the key skills I've developed is integrating APIs into my projects to enhance functionality and provide real-time data. A great example of this is my <a href="https://github.com/Sajjad5037/Weather_watcher" target="_blank" title="Weather Watcher - Real-Time Weather Data Using API Integration">Weather Watcher</a> project, where I built an application that retrieves real-time weather data from an external API. The project uses the <strong>requests</strong> library to make API calls and fetch weather data, which is then processed and displayed to the user. By incorporating this API, I was able to provide users with accurate, up-to-date weather information, including temperature, humidity, and forecast details. This project demonstrates my ability to work with third-party APIs, handle JSON data, and build interactive applications that leverage real-time information for practical use cases.
              </p>
              <p>
                In addition to integrating external APIs, I also developed a project called <a href="https://github.com/Sajjad5037/Pdf-Query-Chatbot" target="_blank" title="PDF Query Chatbot - Using OpenAI API for PDF Interactions">PDF Query Chatbot</a>, which uses the <strong>OpenAI API</strong> to create an interactive chatbot capable of answering queries from PDF documents. This project involves training the model to process and understand PDF content, allowing users to ask questions and receive relevant information. By integrating OpenAI’s API, the chatbot can interpret complex queries and provide precise responses, making it an effective tool for automating document-based interactions. The <strong>OpenAI API</strong> supports model training, ensuring the chatbot becomes more efficient in understanding and processing various types of content over time. This project highlights my ability to work with advanced machine learning APIs, particularly OpenAI, and build intelligent systems that facilitate natural language processing and real-time interaction.
              </p>
            </>
          )}


          <h2
            style={{ cursor: "pointer", display: "flex", alignItems: "center" }}
            onClick={() => setShowMachineLearningContent(!showMachineLearningContent)}
          >
            Machine Learning Model Building
            <a
              href="#"
              onClick={(e) => e.preventDefault()}
              style={{ marginLeft: "8px", color: "blue" }}
            >
              {showMachineLearningContent ? "-" : "+"}
            </a>
          </h2>
          {showMachineLearningContent && (
            <>
              <p>
                Machine learning is a powerful tool for data analysis and predictive modeling. One of my key projects, the <a href="https://github.com/Sajjad5037/Film_Fusion" target="_blank" title="Movie Rating Correlation using Pearson Similarity - Analyze User Preferences with Machine Learning">Movie Rating Correlation Model</a>, analyzes user movie ratings and calculates similarity using the Pearson correlation coefficient. The project allows users to input ratings, visualize correlations through scatter plots, and compare similarity scores between different users. This model helps in identifying users with similar preferences, which can be useful for recommendation systems. Additionally, the project integrates data handling using Pandas, visualization with Matplotlib, and statistical analysis using SciPy for precise similarity measurement.
              </p>
              <p>
                <strong>Fertilizer Analysis for Plant Growth with ANOVA</strong> is an essential project demonstrating statistical analysis to understand how different fertilizers affect plant growth. Using <a href="https://github.com/Sajjad5037/Fertilizer_Plant_Growth_Analysis_with_ANOVA" target="_blank" title="Fertilizer Plant Growth Analysis using ANOVA - Analyze the impact of fertilizers on plant growth with statistical testing">ANOVA</a>, this project evaluates plant growth data from three fertilizers and performs hypothesis testing to identify significant differences. Key features of the project include visualizing growth distributions through boxplots, calculating descriptive statistics, and using Python libraries such as <strong>SciPy</strong> and <strong>Pandas</strong> for statistical analysis and data handling. This analysis can serve as a foundation for understanding fertilizer effects and making data-driven agricultural decisions.
              </p>
              <p>
                <strong>Car Performance Prediction</strong> is a project that leverages statistical analysis and machine learning to predict car mileage (mpg) based on features like horsepower (hp) and weight. Using the <a href="https://github.com/Sajjad5037/Car_Performance_Prediction" target="_blank" title="Car Performance Prediction - Predict car mileage based on horsepower and weight using machine learning">Car Performance Prediction Model</a>, this project analyzes the relationship between horsepower, weight, and miles per gallon (mpg) through Pearson correlation and linear regression. The model evaluates car performance using statistical tests, cleanses the data by removing outliers with Z-scores, and predicts mileage based on input features. The project includes data visualization with Seaborn and Matplotlib, and its results are evaluated using Mean Squared Error and R-squared metrics. This project demonstrates how machine learning can be applied to vehicle performance prediction, making it valuable for automotive analysis and research.
              </p>
            </>
          )}



          <h2
            style={{ cursor: "pointer", display: "flex", alignItems: "center" }}
            onClick={() => setShowWebScrapingContent(!showWebScrapingContent)}
          >
            Web Scraping Projects
            <a 
              href="#"
              onClick={(e) => e.preventDefault()}
              style={{ marginLeft: "8px", color: "blue" }}
            >
              {showWebScrapingContent ? "-" : "+"}
            </a>
          </h2>
          {showWebScrapingContent && (
            <p>
              One of the key skills I've developed is working with web scraping techniques and automating the process of downloading content from the web. A great example of this is my <a href="https://github.com/Sajjad5037/Image_downloader" target="_blank" title="Image Downloader - Automating Image Download from Search Results">Image Downloader</a> project, where I created a Python script that automates the downloading of images based on a search query. The project uses the <strong>requests</strong> and <strong>BeautifulSoup</strong> libraries to scrape web pages, extract image URLs, and download the images to a specified directory. I handle both absolute and relative URLs to ensure that images are downloaded correctly. This project demonstrates my ability to work with web scraping tools, handle requests efficiently, and automate the extraction and downloading of resources from the web.
            </p>
          )}


         <h2
          style={{ cursor: "pointer", display: "flex", alignItems: "center" }}
          onClick={() => setShowDataScienceContent(!showDataScienceContent)}
        >
          Advanced Data Science & AI-Driven Insights
          <a 
            href="#"
            onClick={(e) => e.preventDefault()}
            style={{ marginLeft: "8px", color: "blue" }}
          >
            {showDataScienceContent ? "-" : "+"}
          </a>
        </h2>
        {showDataScienceContent && (
          <p>
            Machine learning is a powerful tool for data analysis and predictive modeling. One of my key projects, the <a href="https://github.com/Sajjad5037/House-Price-Prediction" target="_blank" title="House Price Prediction Model using RandomForestRegressor - Predict House Prices with Machine Learning">House Price Prediction Model</a>, leverages advanced machine learning techniques like one-hot encoding and scaling, combined with a RandomForestRegressor, to accurately predict house prices. The model's performance is evaluated using metrics like MAE and RMSE, and visualized predictions vs. actual prices provide further insights. Additionally, I developed the <a href="https://github.com/Sajjad5037/loan-predictor" target="_blank" title="Loan Approval Prediction Model using Logistic Regression - Predict Loan Approvals with Machine Learning">Loan Approval Prediction Model</a>, which predicts loan approval status based on factors like credit score, income, loan amount, and employment status. Using Logistic Regression, the model is evaluated with accuracy, precision, and recall, along with a confusion matrix to understand the model's predictive capability for loan approvals. Furthermore, I created the <a href="https://github.com/Sajjad5037/Spam-Email-Classification" target="_blank" title="Spam Email Classification using Logistic Regression - Predict Spam Emails with Machine Learning">Spam Email Classification Model</a>, which utilizes TF-IDF vectorization and Logistic Regression to classify emails as spam or non-spam. This model helps in filtering out spam emails effectively, with performance evaluated using accuracy, precision, and recall metrics to ensure robust spam detection.
          </p>
        )}


           <h2
            style={{ cursor: "pointer", display: "flex", alignItems: "center" }}
            onClick={() => setshowDataAnalysisContent(!showDataAnalysisContent)}
          >
            Data Analysis And Data Visulization 
            <a 
              href="#"
              onClick={(e) => e.preventDefault()}
              style={{ marginLeft: "8px", color: "blue" }}
            >
              {showDataAnalysisContent ? "-" : "+"}
            </a>
          </h2>
          {showDataAnalysisContent && (
            <>
              <p>
                Data analysis is an essential tool for uncovering insights and making informed predictions. One of my key projects, the <a href="https://github.com/Sajjad5037/Titanic_Survival_Analysis" target="_blank" title="Titanic Survival Analysis - Predicting Survival Chances on the Titanic using Logistic Regression">Titanic Survival Model</a>, leverages logistic regression to predict the survival probability of passengers aboard the Titanic. The project utilizes the <strong>pandas</strong> library for efficient data manipulation and cleaning, ensuring the dataset is ready for in-depth analysis. Using Pandas, I performed comprehensive exploratory data analysis (EDA) to uncover patterns and identify significant factors influencing survival. Additionally, I integrated data visualization techniques, such as bar charts and heatmaps, to display relationships between variables and outcomes. These visualizations not only improve the model's interpretability but also provide valuable insights into the key factors affecting survival chances. This analysis serves as a foundation for making data-driven decisions and predictions in various applications of statistical modeling.
              </p>
              <p>
                Another project, the <a href="https://github.com/Sajjad5037/Titanic_Survival_Model_Evaluation_Logistic_Regression" target="_blank" title="Titanic Survival Model Evaluation - Evaluating Survival Prediction Accuracy using Logistic Regression">Titanic Survival Model Evaluation</a>, focuses on evaluating the performance and accuracy of survival predictions made using logistic regression. By applying various performance metrics, such as accuracy, precision, and recall, I was able to assess the model's effectiveness in predicting survival outcomes. This project further highlights my ability to not only build models but also rigorously evaluate their performance.
              </p>
              <p>
                In addition, the <a href="https://github.com/Sajjad5037/CustomerDataProcesser" target="_blank" title="Customer Data Processor - Automating Data Cleaning and Analysis">Customer Data Processor</a> automates the cleaning, processing, and analysis of customer data. The project uses the <strong>pandas</strong> library to handle large datasets efficiently, transforming raw data into structured formats ready for analysis. Through this tool, I was able to streamline data preprocessing tasks, making the workflow more efficient and accurate, while ensuring high data quality. This project showcases my ability to manage and process data effectively, helping businesses make informed decisions based on customer insights.
              </p>
            </>
          )}


          <h2
            style={{ cursor: "pointer", display: "flex", alignItems: "center" }}
            onClick={() => setShowPythonAutomationContent(!showPythonAutomationContent)}
          >
            Python Automation Projects
            <a 
              href="#"
              onClick={(e) => e.preventDefault()}
              style={{ marginLeft: "8px", color: "blue" }}
            >
              {showPythonAutomationContent ? "-" : "+"}
            </a>
          </h2>
          {showPythonAutomationContent && (
            <p>
              In this section, I demonstrate how Python can be used to automate repetitive tasks and optimize workflows, ultimately saving time and increasing efficiency. A great example is the <a href="https://github.com/Sajjad5037/WeeklyChoreAssigner" target="_blank" title="Weekly Chore Assigner - Automating Weekly Chore Assignments and Email Notifications">Weekly Chore Assigner</a>. This Python automation script efficiently assigns weekly chores, sends email notifications, and tracks previous assignments. Another example is the <a href="https://github.com/Sajjad5037/scrape_job_listings" target="_blank" title="Job Listings Scraping Automation Tool - Efficient Python Script for Job Market Data Collection and Analysis">Job Listings Scraping Automation Tool</a>, which automates job market data collection by scraping listings from Indeed, organizing them into CSV files for easy analysis and insights. Additionally, the <a href="https://github.com/Sajjad5037/DuesReminderSystem" target="_blank" title="Fee Reminder System - Automated Fee Submission Reminders for Members">Fee Reminder System</a> automates fee reminders, notifying members when their fees are due, ensuring timely submissions and reducing manual tracking efforts.
            </p>
          )}    
        </div>
      </div>
    </Layout>
  );
}

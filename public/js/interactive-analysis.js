// interactive-analysis.js

const apiUrl = 'https://yfinance-stock-market-data.p.rapidapi.com/stock-info';

// Your RapidAPI key
const rapidApiKey = 'd2278c78d6mshef015db14ec8418p113c17jsn4e0d521ad169';

// Function to fetch top and bottom companies data
async function fetchStockData() {
  try {
    const response = await fetch('/get_stock_data'); // Updated URL to match the new route
    const data = await response.json();

    // Process and display data as needed
    displayTopCompanies(data.data);
    displayBottomCompanies(data.data);
  } catch (error) {
    console.error('Error fetching stock data:', error);
  }
}

// Function to display top companies
function displayTopCompanies(topCompaniesData) {
  const topCompaniesTable = document.getElementById('topCompaniesTable');
  // Clear existing table rows
  topCompaniesTable.innerHTML = '';

  // Iterate through the data and add rows to the table
  topCompaniesData.forEach((company) => {
    const row = topCompaniesTable.insertRow();
    row.insertCell(0).textContent = company.name;
    row.insertCell(1).textContent = company.symbol;
    row.insertCell(2).textContent = company.change;
    row.insertCell(3).textContent = company.changePercentage;
  });
}

// Function to display bottom companies
function displayBottomCompanies(bottomCompaniesData) {
  const bottomCompaniesTable = document.getElementById('bottomCompaniesTable');
  // Clear existing table rows
  bottomCompaniesTable.innerHTML = '';

  // Iterate through the data and add rows to the table
  bottomCompaniesData.forEach((company) => {
    const row = bottomCompaniesTable.insertRow();
    row.insertCell(0).textContent = company.name;
    row.insertCell(1).textContent = company.symbol;
    row.insertCell(2).textContent = company.change;
    row.insertCell(3).textContent = company.changePercentage;
  });
}

// Fetch stock data when the page loads
window.addEventListener('load', fetchStockData);

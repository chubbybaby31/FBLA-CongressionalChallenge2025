const express = require('express');
const bodyParser = require('body-parser');
const fs = require('fs').promises;
const path = require('path');
const cors = require('cors'); // Add this line

const app = express();
const PORT = 3001;
const DATA_FILE = path.join(__dirname, 'financial_data.txt');

app.use(bodyParser.json());
app.use(cors()); // Add this line to enable CORS for all routes

// Initialize data structure
let financialData = {
  currentBalance: 0,
  monthlyIncome: 0,
  monthlyExpense: 0,
  transactions: []
};

// Load data from file on server start
async function loadData() {
  try {
    const data = await fs.readFile(DATA_FILE, 'utf8');
    financialData = JSON.parse(data);
  } catch (error) {
    console.log('No existing data file, starting with empty data');
  }
}

// Save data to file
async function saveData() {
  await fs.writeFile(DATA_FILE, JSON.stringify(financialData, null, 2));
}

// Get current financial data
app.get('/api/financial-data', (req, res) => {
  res.json(financialData);
});

// Update monthly income
app.post('/api/update-income', (req, res) => {
  const { amount } = req.body;
  financialData.monthlyIncome = amount;
  saveData();
  res.json({ success: true, newIncome: financialData.monthlyIncome });
});

// Update monthly expense
app.post('/api/update-expense', (req, res) => {
  const { amount } = req.body;
  financialData.monthlyExpense = amount;
  saveData();
  res.json({ success: true, newExpense: financialData.monthlyExpense });
});

// Add transaction
app.post('/api/add-transaction', (req, res) => {
  const { amount, description, type } = req.body;
  const transaction = { amount, description, type, date: new Date().toISOString() };
  financialData.transactions.push(transaction);
  
  if (type === 'income') {
    financialData.currentBalance += amount;
  } else if (type === 'expense') {
    financialData.currentBalance -= amount;
  }

  saveData();
  res.json({ success: true, newBalance: financialData.currentBalance, transaction });
});

// Add money to balance (apart from monthly income)
app.post('/api/add-to-balance', (req, res) => {
  const { amount } = req.body;
  financialData.currentBalance += amount;
  saveData();
  res.json({ success: true, newBalance: financialData.currentBalance });
});

// Start server
app.listen(PORT, async () => {
  await loadData();
  console.log(`Server running on port ${PORT}`);
});
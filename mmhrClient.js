const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');
const crypto = require('crypto');
const { saveMmhrAccount, updateMmhrToken } = require('./db');

const MMHR_API_URL = process.env.MMHR_API_URL || 'http://localhost:5000';

function generatePassword() {
  return crypto.randomBytes(12).toString('hex');
}

async function getOrCreateMmhrToken(chatId, firstName, existingUser) {
  if (existingUser && existingUser.mmhr_token) {
    return existingUser.mmhr_token;
  }

  const email = `tg_${chatId}@mmhr.local`;
  const username = `tg_${chatId}_${(firstName || 'user').replace(/\s+/g, '')}`;
  const password = (existingUser && existingUser.mmhr_password) || generatePassword();

  if (existingUser && existingUser.mmhr_email) {
    try {
      const loginRes = await axios.post(`${MMHR_API_URL}/api/auth/login`, {
        email: existingUser.mmhr_email,
        password: existingUser.mmhr_password
      });
      const token = loginRes.data.token;
      await updateMmhrToken(chatId, token);
      return token;
    } catch (err) {
      console.error('فشل تسجيل الدخول بحساب موجود، هنعمل حساب جديد:', err.message);
    }
  }

  try {
    await axios.post(`${MMHR_API_URL}/api/auth/register`, { username, email, password });
  } catch (err) {
    if (!err.response || err.response.status !== 409) {
      throw new Error('فشل إنشاء الحساب في MMHR: ' + err.message);
    }
  }

  const loginRes = await axios.post(`${MMHR_API_URL}/api/auth/login`, { email, password });
  const token = loginRes.data.token;
  await saveMmhrAccount(chatId, email, password, token);
  return token;
}

async function uploadFileToMmhr(token, filePath, fileName) {
  const form = new FormData();
  form.append('file', fs.createReadStream(filePath), fileName);

  const res = await axios.post(`${MMHR_API_URL}/api/documents/upload`, form, {
    headers: { ...form.getHeaders(), Authorization: `Bearer ${token}` }
  });
  return res.data.documentId;
}

async function waitForProcessedText(token, documentId, maxTries = 15) {
  for (let i = 0; i < maxTries; i++) {
    await new Promise((resolve) => setTimeout(resolve, 2000));
    const res = await axios.get(`${MMHR_API_URL}/api/documents`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    const doc = res.data.documents.find((d) => d.id === documentId);
    if (doc && doc.status === 'completed') {
      return doc.processed_text;
    }
    if (doc && doc.status === 'failed') {
      throw new Error('فشلت معالجة الملف في MMHR');
    }
  }
  throw new Error('استغرقت المعالجة وقت طويل، جرب تاني بعد شوية');
}

module.exports = { getOrCreateMmhrToken, uploadFileToMmhr, waitForProcessedText };

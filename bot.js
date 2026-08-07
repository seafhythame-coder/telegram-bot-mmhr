require('dotenv').config();
const TelegramBot = require('node-telegram-bot-api');
const fs = require('fs');
const path = require('path');
const { setupDatabase, saveUser, getUser, pool } = require('./db');
const { getOrCreateMmhrToken, uploadFileToMmhr, waitForProcessedText } = require('./mmhrClient');

const token = process.env.BOT_TOKEN;

if (!token || token === 'ضع_التوكن_هنا') {
  console.error('❌ لازم تحط توكن البوت في ملف .env أولاً');
  process.exit(1);
}

const bot = new TelegramBot(token, { polling: true });

const tempDir = path.join(__dirname, 'temp_downloads');
if (!fs.existsSync(tempDir)) fs.mkdirSync(tempDir);

setupDatabase();

console.log('✅ البوت شغال ويستقبل الرسائل...');

bot.onText(/\/start/, async (msg) => {
  const chatId = msg.chat.id;
  const username = msg.from.username || null;
  const firstName = msg.from.first_name || 'صديقنا';
  await saveUser(chatId, username, firstName);
  bot.sendMessage(chatId, `أهلاً ${firstName}! 👋\n\nابعتلي أي ملف PDF أو Word أو صورة وهعالجه وأرجعلك النص.`);
});

bot.onText(/\/help/, (msg) => {
  bot.sendMessage(msg.chat.id, 'ابعتلي ملف (PDF / Word / صورة) وهعالجه تلقائياً.');
});

bot.onText(/\/mystats/, async (msg) => {
  const chatId = msg.chat.id;
  const user = await getUser(chatId);
  if (!user) {
    bot.sendMessage(chatId, 'مافيش بيانات محفوظة، ابعت /start أولاً.');
  } else {
    bot.sendMessage(chatId, `📊 الاسم: ${user.first_name}\nحساب MMHR: ${user.mmhr_email || 'لسه ما اتعمل'}`);
  }
});

async function handleIncomingFile(msg, fileId, suggestedName) {
  const chatId = msg.chat.id;
  let localPath;
  try {
    bot.sendMessage(chatId, '📥 استلمت الملف، جاري رفعه ومعالجته...');
    localPath = await bot.downloadFile(fileId, tempDir);
    const fileName = suggestedName || path.basename(localPath);
    const user = await getUser(chatId);
    const mmhrToken = await getOrCreateMmhrToken(chatId, msg.from.first_name, user);
    const documentId = await uploadFileToMmhr(mmhrToken, localPath, fileName);
    bot.sendMessage(chatId, '⏳ الملف بيتعالج دلوقتي...');
    const processedText = await waitForProcessedText(mmhrToken, documentId);
    if (processedText && processedText.length > 0) {
      const chunks = processedText.match(/[\s\S]{1,3500}/g) || [processedText];
      for (const chunk of chunks) {
        await bot.sendMessage(chatId, chunk);
      }
      bot.sendMessage(chatId, '✅ خلصت المعالجة!');
    } else {
      bot.sendMessage(chatId, '⚠️ اتعالج الملف بس مافيش نص واضح جواه.');
    }
  } catch (err) {
    console.error('❌ خطأ:', err.message);
    bot.sendMessage(chatId, `❌ صار خطأ: ${err.message}`);
  } finally {
    if (localPath && fs.existsSync(localPath)) fs.unlinkSync(localPath);
  }
}

bot.on('document', (msg) => handleIncomingFile(msg, msg.document.file_id, msg.document.file_name));
bot.on('photo', (msg) => {
  const photo = msg.photo[msg.photo.length - 1];
  handleIncomingFile(msg, photo.file_id, `photo_${Date.now()}.jpg`);
});
bot.on('message', (msg) => {
  if (msg.text && !msg.text.startsWith('/')) {
    bot.sendMessage(msg.chat.id, 'ابعتلي ملف (PDF / Word / صورة) عشان أعالجه.');
  }
});

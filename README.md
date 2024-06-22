<h1 class="atx" id="deploy-veloce">Deploy veloce</h1>
<p>Aggiungi al tuo gruppo il bot <a href="https://t.me/pupucounter_bot">@pupucounter_bot</a> e rendilo admin in modo che possa vedere i messaggi, funziona anche nelle chat private ma avrai solo le tue statistiche</p>
<h1 class="atx" id="deploy-personale">Deploy personale</h1>
<p>Se non vuoi usare il bot per motivi di privacy, puoi scaricare i file e seguire la guida di seguito</p>
<h3 class="atx" id="creare-un-file-env">Creare un file .env</h3>
<p>Il file dotenv serve per conservare i dati sensibili, bisogna sempre tenere privati questi file.</p>
<p>Una volta creato, aprire il file e in una riga scrivere <code>BOT_TOKEN=TokenChePrenderemoTraPoco</code> in modo che il bot sappia a chi deve fare riferimento</p>
<h3 class="atx" id="creare-un-token-per-il-bot">Creare un token per il bot</h3>
<p>Contattiamo il bot <a href="https://t.me/BotFather">@BotFather</a> per creare il bot nei server telegram, questo ci darà un token per il bot che ci dirà di non condividere, questo va inserito nel file creato in precedenza dopo il simbolo dell'uguale</p>
<h3 class="atx" id="far-partire-il-bot">Far partire il bot</h3>
<p>Per far partire il bot, dopo aver installato python e le sue prime dipendenze, spostarsi nella cartella della repository e scrivere nel terminale <code>pip install -r requirements.txt</code> in modo da far scaricare tutte le dipendenze necessarie.</p>
<p>Dopo aver installato tutto si può far partire il bot, per avviarlo basta scrivere nel terminale <code>python caccapupu.py</code>, questo metodo però vedrà il bot chiudersi insieme alla console, per ovviare si può usare il comando nohup per dire al terminale che deve staccare l'output dal terminale, possiamo usarlo con il comando <code>nohup python caccapupu.py &amp;</code></p>
<h3 class="atx" id="recap">RECAP</h3>
<p>Scaricare tutti i file</p>
<p>Creare il file <code>.env</code></p>
<p>Contattare il bot telegram botfather per creare il token</p>
<p>Inserire il token nel file env</p>
<p>Installare le dipendenze</p>
<p>Avviare il bot</p>

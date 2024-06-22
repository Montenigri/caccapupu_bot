# Deploy veloce

Aggiungi al tuo gruppo il bot [@pupucounter_bot](https://t.me/pupucounter_bot) e rendilo admin in modo che possa vedere i messaggi, funziona anche nelle chat private ma avrai solo le tue statistiche

# Deploy personale

Se non vuoi usare il bot per motivi di privacy, puoi scaricare i file e seguire la guida di seguito, alla fine è presente un recap dei passi da affrontare

### Creare un file .env

Il file dotenv serve per conservare i dati sensibili, bisogna sempre tenere privati questi file.

Una volta creato, aprire il file e in una riga scrivere `BOT_TOKEN=TokenChePrenderemoTraPoco` in modo che il bot sappia a chi deve fare riferimento

### Creare un token per il bot

Contattiamo il bot [@BotFather](https://t.me/BotFather) per creare il bot nei server telegram, questo ci darà un token per il bot che ci dirà di non condividere, questo va inserito nel file creato in precedenza dopo il simbolo dell'uguale

### Far partire il bot

Per far partire il bot, dopo aver installato python e le sue prime dipendenze, spostarsi nella cartella della repository e scrivere nel terminale `pip install -r requirements.txt` in modo da far scaricare tutte le dipendenze necessarie.

Dopo aver installato tutto si può far partire il bot, per avviarlo basta scrivere nel terminale `python caccapupu.py`, questo metodo però vedrà il bot chiudersi insieme alla console, per ovviare si può usare il comando nohup per dire al terminale che deve staccare l'output dal terminale, possiamo usarlo con il comando `nohup python caccapupu.py &`

### RECAP

Scaricare tutti i file

Creare il file `.env`

Contattare il bot telegram botfather per creare il token

Inserire il token nel file env

Installare le dipendenze

Avviare il bot
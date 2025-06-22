# Data access
from zipfile import ZipFile
from io import BytesIO
import urllib.request as urllib2
# Cleaning
import pandas as pd
import datetime as dt
# Structure XML
import xml.etree.ElementTree as et
# Email
import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import os
# Visuals
import matplotlib.pyplot as plt
# import plotly.graph_objects as go
from pretty_html_table import build_table

#####################
##### PRIX LIVE #####
#####################

url = urllib2.urlopen('https://donnees.roulez-eco.fr/opendata/instantane').read()
file = ZipFile(BytesIO(url))

# NB : MAJ entre 4h et 11h
source_xml = file.open('PrixCarburants_instantane.xml')

source = source_xml.read()

ids = []
villes = []
adresses = []
carburant = []
tarif = []
majs = []

pdv_liste = et.fromstring(source)

pdvs = pdv_liste.findall('.//pdv')
for pdv in pdvs:
    if pdv.attrib['cp'] in ('69440', '69700'):
        station = pdv.attrib['id']
        ville = pdv.find('ville').text
        addresse = pdv.find('adresse').text
        all_prix = pdv.findall('prix')
        for prix in all_prix:
            if prix.attrib['nom'] == 'Gazole':
                ids.append(station)
                villes.append(ville)
                adresses.append(addresse)
                carburant.append(prix.attrib['nom'])
                tarif.append(prix.attrib['valeur'])
                majs.append(prix.attrib['maj'])

live = pd.DataFrame(list(zip(villes, adresses, ids, carburant, tarif, majs)), columns = ['Villes', 'Adresses', 'ID', 'Carburants','Prix', 'MAJ'])
live['Villes'] = live['Villes'].str.upper()
live = live[live['Villes'].isin(['MORNANT', 'GIVORS'])]
live = live.sort_values(['Prix'], ascending = True)

# Correspondances
live.loc[live['ID'] == '69440001', 'Enseignes'] = 'RENAULT'
live.loc[live['ID'] == '69700001', 'Enseignes'] = 'CARREFOUR'
live.loc[live['ID'] == '69700005', 'Enseignes'] = 'INTERMARCHE'

live = live[['Prix', 'Enseignes', 'Villes', 'MAJ']]

###########################
##### PRIX DE L'ANNEE #####
###########################

annee = dt.date.today().year

url = urllib2.urlopen('https://donnees.roulez-eco.fr/opendata/annee').read()
file = ZipFile(BytesIO(url))

# NB : MAJ entre 4h et 11h
source_xml = file.open('PrixCarburants_annuel_' + str(annee) + '.xml')

source = source_xml.read()

stations = []
villes = []
dates = []
carburant = []
tarif = []

pdv_liste = et.fromstring(source)

pdvs = pdv_liste.findall('.//pdv')
for pdv in pdvs:
    if pdv.attrib['id'] in ('69700001', '69700005', '69440001'):
        ville = pdv.find('ville').text
        histo_prix = pdv.findall('.//prix')
        for prix in histo_prix:
            if prix.attrib['nom'] == 'Gazole':
                stations.append(pdv.attrib['id'])
                villes.append(ville)
                carburant.append(prix.attrib['nom'])
                dates.append(prix.attrib['maj'])
                tarif.append(prix.attrib['valeur'])

df = pd.DataFrame(list(zip(stations, carburant, villes, tarif, dates)), columns = ['ID', 'Carburants', 'Villes', 'Prix', 'Dates'])

# Correspondances
df.loc[df['ID'] == '69440001', 'Enseignes'] = 'RENAULT'
df.loc[df['ID'] == '69700001', 'Enseignes'] = 'CARREFOUR'
df.loc[df['ID'] == '69700005', 'Enseignes'] = 'INTERMARCHE'

df = df[['Enseignes', 'Dates', 'Prix']]
df['Prix'] = df['Prix'].astype(float)
df['Dates'] = pd.to_datetime(df['Dates'], yearfirst = True).dt.date
df = df.drop_duplicates(['Enseignes', 'Dates'])

df = df.set_index(['Enseignes', 'Dates'])
df = df.unstack('Enseignes')
df = df.fillna(method = 'ffill')
df = df.iloc[-21:, :]
df.columns = df.columns.droplevel(0)
df = df.reset_index()

##########################
##### DESIGN GRAFICS #####
##########################

# graf = go.Figure()
# graf.update_layout(title = 'Evolution prix du gazole')
# graf.add_trace(go.Scatter(x = df['Dates'], y = df['RENAULT'].values, line_shape = 'hv', name = 'RENAULT'))
# graf.add_trace(go.Scatter(x = df['Dates'], y = df['CARREFOUR'].values, line_shape = 'hv', name = 'CARREFOUR'))
# graf.add_trace(go.Scatter(x = df['Dates'], y = df['INTERMARCHE'].values, line_shape = 'hv', name = 'INTERMARCHE'))

# graf.write_image('essence.png')

# Avec Matplotlib
plt.plot(df['RENAULT'].values, label ='RENAULT', color = 'pink')
plt.plot(df['CARREFOUR'].values, '-.', label ='CARREFOUR', color = 'b')
plt.plot(df['INTERMARCHE'].values, '-.', label ='INTERMARCHE', color = 'r')
plt.savefig("essence.png")

############################
##### ENVOI DE L'EMAIL #####
############################

# Images à envoyer
with open('essence.png', 'rb') as file:
    msgImage = MIMEImage(file.read())
    msgImage.add_header('Content-ID', '<essence>')

# Texte à envoyer
msg = """
Bonjour,<br><br>
Le prix du Gazole de vos stations préférées :<br><br>
{}<br>
<br>
Evolution du prix depuis 4 semaines :<br><br>
<img src='cid:essence'>
""".format(build_table(live, 'blue_light', font_size='11px'))

msgtext = MIMEText(msg, 'html')

msg = MIMEMultipart()
msg['Subject'] = 'MAJ prix Diesel'
msg.attach(msgtext)
msg.attach(msgImage)

port = 465
smtp_server = 'smtp.gmail.com'
user_email = os.environ.get('user_email')
recipients = os.environ.get('recipients')
email_token = os.environ.get('email_token')

try:
    context = ssl.create_default_context() # ne fonctionne pas
    server = smtplib.SMTP_SSL(smtp_server, port, context = context)
    server.login(user_email, email_token)
    server.sendmail(user_email, recipients.split(','), msg.as_string())
except:
    print('Something went wrong...')




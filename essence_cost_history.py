import pandas as pd
import xml.etree.ElementTree as et

# https://www.prix-carburants.gouv.fr/rubrique/opendata/

# ouvrir le fichier xml dans vscode pour voir la structure des balises

for annee in range(2007, 2022):

    file = './data/carburants/PrixCarburants_annuel_'+str(annee)+'.xml'

    with open(file, 'r') as f:
        source = f.read()

    dates = []
    carburant = []
    tarif = []

    pdv_liste = et.fromstring(source)

    pdvs = pdv_liste.findall('.//pdv')
    for pdv in pdvs:
        if pdv.attrib['id'] == '69700001':
            addresse = pdv.find('adresse').text
            histo_prix = pdv.findall('.//prix')
            for prix in histo_prix:
                carburant.append(prix.attrib['nom'])
                dates.append(prix.attrib['maj'])
                tarif.append(prix.attrib['valeur'])
            break

    df = pd.DataFrame(list(zip(carburant, dates, tarif)), columns = ['Carburants', 'Dates', 'Prix'])
    print(addresse)
    df.to_csv('./data/carburants/carrefour_'+str(annee)+'.csv', index = False, sep = ';')
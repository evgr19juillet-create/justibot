import streamlit as st
import google.generativeai as genai
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
import requests
import uuid

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Justibots",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- PROTECTION ANTI-COPIE ET NETTOYAGE LEGER ---
st.markdown("""
<style>
    /* 1. Bloque la sélection sur TOUTE la page par défaut */
    html, body, [class*="css"] {
        -webkit-user-select: none !important;
        -moz-user-select: none !important;
        -ms-user-select: none !important;
        user-select: none !important;
    }
    
    /* 2. Réautorise la saisie UNIQUEMENT sur les champs actifs */
    input:not([disabled]), textarea:not([disabled]) {
        -webkit-user-select: text !important;
        -moz-user-select: text !important;
        -ms-user-select: text !important;
        user-select: text !important;
    }

    /* 3. VERROUILLAGE de la case d'aperçu SANS bloquer le scroll */
    textarea[disabled] {
        -webkit-user-select: none !important;
        -moz-user-select: none !important;
        -ms-user-select: none !important;
        user-select: none !important;
    }

    /* 4. Rend le surlignage invisible */
    textarea[disabled]::selection { background-color: transparent !important; color: inherit !important; }

    /* 5. CACHE SEULEMENT LE PETIT BOUTON "MADE WITH STREAMLIT" EN BAS A DROITE */
    div[class^="viewerBadge"] { display: none !important; }

</style>
<script>
    /* Bloque le clic droit et les raccourcis de copie */
    document.addEventListener('contextmenu', event => event.preventDefault());
    document.addEventListener('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && (e.key === 'c' || e.key === 'C' || e.key === 'a' || e.key === 'A' || e.key === 'x' || e.key === 'X')) {
            e.preventDefault();
        }
    });
    document.addEventListener('copy', function(e) { e.preventDefault(); });
</script>
""", unsafe_allow_html=True)

# --- 2. RÉCUPÉRATION DES SECRETS ---
try:
    api_key = st.secrets["GEMINI_KEY"]
    user_email = st.secrets["EMAIL_ADDRESS"]
    user_password = st.secrets["EMAIL_PASSWORD"]
    sumup_api_key = st.secrets["SUMUP_API_KEY"]
    sumup_merchant_code = st.secrets["SUMUP_MERCHANT_CODE"]
except Exception:
    st.error("⚠️ Les secrets (clés) ne sont pas configurés. Vérifiez sur Streamlit.")
    st.stop()

genai.configure(api_key=api_key)

# --- 3. DÉTECTION AUTOMATIQUE DU MODÈLE ---
@st.cache_resource
def obtenir_modele():
    try:
        modeles_autorises = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for nom in modeles_autorises:
            if '1.5-flash' in nom:
                return nom.replace('models/', '')
        if modeles_autorises:
            return modeles_autorises[0].replace('models/', '')
        return 'gemini-1.5-flash'
    except Exception:
        return 'gemini-1.5-flash'

MODELE_AUTORISE = obtenir_modele()

# --- LOGIQUE DE PAIEMENT ---
query_params = st.query_params
est_paye = query_params.get("payment") == "success"

# --- 4. FONCTIONS ---
def creer_paiement_sumup(montant=5.00):
    url = "https://api.sumup.com/v0.1/checkouts"
    headers = {
        "Authorization": f"Bearer {sumup_api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "checkout_reference": str(uuid.uuid4()),
        "amount": montant,
        "currency": "EUR",
        "merchant_code": sumup_merchant_code,
        "description": "Génération de Mise en Demeure - Justibots",
        "return_url": "https://justibot.fr/?payment=success",
        "hosted_checkout": {"enabled": True}
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code in [200, 201]:
            return response.json().get("hosted_checkout_url")
        return None
    except:
        return None

def envoyer_mail(destinataire, sujet, corps, fichiers_joints=None):
    msg = MIMEMultipart()
    msg['From'] = user_email
    msg['To'] = destinataire
    msg['Subject'] = sujet
    msg.attach(MIMEText(corps, 'plain'))

    # Ajout des pièces jointes au mail
    if fichiers_joints:
        for fichier in fichiers_joints:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(fichier.getvalue())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="{fichier.name}"')
            msg.attach(part)

    try:
        server = smtplib.SMTP('smtp.hostinger.com', 587)
        server.starttls()
        server.login(user_email, user_password)
        server.send_message(msg)
        server.quit()
        return True, "✅ Courrier et preuves envoyés avec succès !"
    except Exception as e:
        return False, f"Erreur d'envoi : {str(e)}"

def analyse_ia(text):
    model = genai.GenerativeModel(MODELE_AUTORISE)
    try:
        prompt = f"Analyse ce problème juridique et classe-le. Réponds juste par la catégorie. Contexte: {text}"
        return model.generate_content(prompt).text.strip()
    except Exception as e:
        return f"Erreur d'analyse IA : {str(e)}"

def generer_courrier(probleme, categorie, user_infos):
    model = genai.GenerativeModel(MODELE_AUTORISE)
    date_jour = datetime.now().strftime("%d/%m/%Y")
    
    en_tete = f"{user_infos['nom']}\n"
    en_tete += f"{user_infos['adresse']}\n"
    en_tete += f"{user_infos['ville']}\n"
    en_tete += f"Email : {user_infos['email']}\n\n"
    en_tete += f"À l'attention du Service Client / SAV\nDate : {date_jour}\n\n"
    
    prompt = f"""
    Tu es un avocat expert en droit français. 
    Le litige concerne : {categorie}.
    Les faits racontés par le client : "{probleme}"

    Rédige UNIQUEMENT le corps de la lettre de mise en demeure.
    
    CONSIGNES STRICTES :
    1. Commence directement par "Objet : Mise en demeure formelle - [Résumé de l'objet]"
    2. Enchaîne avec "Madame, Monsieur," puis le texte à la première personne ("Je").
    3. NE LAISSE AUCUN CROCHET NI TEXTE À TROUS. N'invente pas de numéro de commande s'il n'y en a pas.
    4. Adopte un ton très formel, froid et menaçant juridiquement.
    5. Cite les articles de loi adaptés (Code de la Consommation, Code Civil...).
    6. Exige la résolution du problème sous 8 jours.
    7. Termine par une formule de politesse classique et écris simplement "{user_infos['nom']}" tout en bas.
    """
    try:
        corps_lettre = model.generate_content(prompt).text.strip()
        lettre_finale = en_tete + corps_lettre
        return lettre_finale
    except Exception as e:
        return f"Erreur IA : {str(e)}"

# --- 5. INTERFACE ---
with st.sidebar:
    st.title("🧭 Navigation")
    choix_page = st.radio("Aller vers :", ["✍️ Générateur de Courrier", "📚 Ressources Juridiques", "⚖️ Mentions Légales & CGV"])
    st.divider()

if choix_page == "✍️ Générateur de Courrier":
    st.title("⚖️ Justibots : Assistant Juridique")
    
    with st.sidebar:
        st.header("👤 Vos Coordonnées")
        nom_client = st.text_input("Nom & Prénom")
        adresse_client = st.text_input("Adresse (Rue)")
        ville_client = st.text_input("Code Postal & Ville")
        email_client_perso = st.text_input("Votre Email")

    col1, col2 = st.columns([1, 1])
    with col1:
        message_litige = st.text_area("Expliquez la situation en détail...", height=250)
    with col2:
        email_sav = st.text_input("Email du SAV adverse")
        fichiers_preuves = st.file_uploader("📎 Ajouter des preuves (Photos, Factures...)", type=["jpg", "jpeg", "png", "pdf"], accept_multiple_files=True)
        st.write("") 
        
        if st.button("Générer ma Mise en Demeure ⚡", type="primary", use_container_width=True):
            if not nom_client or not adresse_client or not ville_client or not email_client_perso or not message_litige:
                st.error("⚠️ Veuillez remplir TOUTES vos coordonnées à gauche et la description du problème.")
            else:
                with st.spinner("L'avocat IA rédige votre courrier..."):
                    cat = analyse_ia(message_litige)
                    infos_client = {"nom": nom_client, "adresse": adresse_client, "ville": ville_client, "email": email_client_perso}
                    
                    st.session_state['preuves'] = fichiers_preuves
                    
                    resultat_courrier = generer_courrier(message_litige, cat, infos_client)
                    st.session_state['courrier'] = resultat_courrier
                    st.session_state['sujet'] = f"MISE EN DEMEURE - {cat} - {nom_client}"
                    
                    lien_sumup = creer_paiement_sumup(montant=5.00)
                    if lien_sumup:
                        st.session_state['lien_paiement'] = lien_sumup
                        st.success("Courrier généré avec succès ! Lisez les instructions ci-dessous.")
                    else:
                        st.error("⚠️ Erreur de connexion avec le terminal de paiement SumUp.")

    if 'courrier' in st.session_state:
        st.divider()
        if not est_paye:
            st.subheader("🔒 Votre courrier est prêt !")
            st.warning("Pour débloquer l'envoi, le téléchargement et les modifications, merci de régler les frais de service.")
            
            st.text_area("Aperçu complet (Lecture seule, Copie désactivée) :", value=st.session_state['courrier'], height=400, disabled=True)
            
            if 'lien_paiement' in st.session_state:
                st.link_button("💳 Payer avec SumUp (5,00€) pour débloquer", st.session_state['lien_paiement'], type="primary", use_container_width=True)
                st.caption("Une fois le paiement effectué, vous serez redirigé automatiquement ici.")
        else:
            st.subheader("📝 Votre courrier débloqué")
            st.success("✅ Paiement confirmé ! Vous pouvez maintenant modifier et envoyer votre courrier.")
            courrier_final = st.text_area("Relisez et modifiez si besoin :", value=st.session_state['courrier'], height=400)
            sujet_final = st.text_input("Objet du mail :", value=st.session_state['sujet'])
            
            col_send, col_down = st.columns([1, 1])
            with col_down:
                st.download_button("📥 Télécharger le texte", data=courrier_final, file_name="Mise_en_demeure.txt", mime="text/plain", use_container_width=True)
            with col_send:
                if st.button("🚀 Envoyer le mail au SAV", use_container_width=True):
                    if not email_sav:
                        st.error("Il manque l'email du destinataire !")
                    else:
                        with st.spinner("Envoi en cours..."):
                            preuves_jointes = st.session_state.get('preuves', [])
                            ok, msg = envoyer_mail(email_sav, sujet_final, courrier_final, preuves_jointes)
                            st.success(msg) if ok else st.error(msg)

elif choix_page == "📚 Ressources Juridiques":
    st.title("📚 Ressources & Droits")
    st.markdown("Consultez nos fiches pratiques pour comprendre vos droits face aux litiges du quotidien.")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📦 Colis non reçu", 
        "✈️ Vol annulé/retardé", 
        "🛠️ Produit défectueux", 
        "🏠 Caution non rendue"
    ])
    
    with tab1:
        st.header("Colis marqué comme 'livré' mais non reçu, ou perdu")
        st.info("💡 **La règle d'or :** C'est le vendeur qui est responsable, pas le transporteur !")
        st.markdown("""
        **Que dit la loi ?** Selon l'article L216-1 du Code de la consommation, le vendeur est responsable de la livraison du bien. Si le transporteur (La Poste, Colissimo, Mondial Relay...) perd le colis ou prétend l'avoir livré à tort, c'est au vendeur de vous rembourser ou de vous renvoyer le produit. Il ne peut pas vous demander de vous débrouiller avec le transporteur.
        """)
        
    with tab2:
        st.header("Vol retardé ou annulé")
        st.info("💡 **La règle d'or :** Vous avez droit à une indemnisation financière, même si la compagnie vous a remboursé ou échangé votre billet !")
        st.markdown("""
        **Que dit la loi ?**
        Le règlement européen (CE) n° 261/2004 protège les passagers de manière très stricte. Si votre vol a plus de 3 heures de retard à l'arrivée, ou s'il est annulé moins de 14 jours avant le départ, vous pouvez réclamer :
        * **250 €** pour les vols jusqu'à 1 500 km.
        * **400 €** pour les vols entre 1 500 km et 3 500 km.
        * **600 €** pour les vols de plus de 3 500 km.
        """)
        
    with tab3:
        st.header("Produit en panne ou défectueux")
        st.info("💡 **La règle d'or :** La garantie légale de conformité dure 2 ans pour les produits neufs !")
        st.markdown("""
        **Que dit la loi ?**
        Les articles L217-3 et suivants du Code de la consommation obligent le **vendeur** (et non le fabricant) à réparer, remplacer ou rembourser un produit qui tombe en panne dans les 2 ans suivant l'achat. 
        """)
        
    with tab4:
        st.header("Dépôt de garantie (caution) non rendu")
        st.info("💡 **La règle d'or :** Le propriétaire ne peut pas conserver votre caution sans fournir de justificatifs (devis ou factures réelles).")
        st.markdown("""
        **Que dit la loi ?**
        La loi du 6 juillet 1989 encadre très strictement les délais de restitution :
        * **1 mois maximum** si l'état des lieux de sortie est identique à l'état des lieux d'entrée.
        * **2 mois maximum** s'il y a des dégradations notées.
        """)

elif choix_page == "⚖️ Mentions Légales & CGV":
    st.title("⚖️ Mentions Légales & Conditions Générales de Vente")
    st.markdown("""
    ### 1. Éditeur du site
    Ce site est édité et géré par **Valentin Remiot**, agissant en tant qu'éditeur de la solution logicielle Justibot.
    * **Adresse :** 18 place du dr hugier, 51120 Sézanne, France.
    * **Contact email :** valentin.jacques51210@gmail.com
    * **Hébergeur :** Le nom de domaine justibot.fr est hébergé par Hostinger. L'application est propulsée par Streamlit Community Cloud.

    ### 2. Description du service
    Justibot propose un outil d'assistance à la rédaction de courriers juridiques (mises en demeure) générés par une Intelligence Artificielle.
    **Attention :** Justibot n'est pas un cabinet d'avocats. L'outil fournit des modèles de lettres générés automatiquement sur la base des éléments fournis par l'utilisateur. L'éditeur ne saurait être tenu responsable de l'issue d'un litige ni de l'exactitude des fondements juridiques proposés par l'algorithme. Il s'agit d'une obligation de moyens et non de résultat.

    ### 3. Tarification et Paiement
    Le service est facturé à l'acte au tarif unique de **5,00 € TTC** par courrier généré et débloqué.
    Le paiement est assuré de manière entièrement sécurisée par notre prestataire de services de paiement certifié **SumUp**. Aucune donnée bancaire n'est stockée sur nos serveurs.

    ### 4. Renonciation au droit de rétractation
    Conformément à l'article L221-28 du Code de la consommation, le droit de rétractation ne peut être exercé pour les contrats de fourniture d'un contenu numérique non fourni sur un support matériel dont l'exécution a commencé après accord préalable exprès du consommateur.
    En validant le paiement de 5,00 € pour débloquer votre courrier, **vous acceptez expressément que le service soit exécuté immédiatement et vous renoncez par conséquent à votre droit de rétractation de 14 jours**. Aucun remboursement ne pourra être exigé après le déblocage du document.

    ### 5. Protection des données personnelles (RGPD)
    Les informations saisies dans le formulaire (Nom, Adresse, Email, faits du litige) sont utilisées de manière éphémère et automatisée pour interroger l'Intelligence Artificielle (Google Gemini) et générer votre document. Ces données ne sont **ni stockées dans une base de données, ni revendues à des tiers**.
    """)

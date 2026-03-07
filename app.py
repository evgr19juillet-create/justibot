# --- PROTECTION ANTI-COPIE (CSS & JS OPTIMISÉS) ---
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
        /* pointer-events: none !important; SUPPRIMÉ POUR POUVOIR FAIRE DÉFILER LE TEXTE */
    }

    /* 4. Rend le surlignage 100% invisible en cas de forçage */
    textarea[disabled]::selection {
        background-color: transparent !important;
        color: inherit !important;
    }
</style>
<script>
    /* Bloque le clic droit */
    document.addEventListener('contextmenu', event => event.preventDefault());
    
    /* Bloque les raccourcis clavier de copie (Ctrl+C, Ctrl+A) */
    document.addEventListener('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && (e.key === 'c' || e.key === 'C' || e.key === 'a' || e.key === 'A' || e.key === 'x' || e.key === 'X')) {
            e.preventDefault();
        }
    });
    
    /* Sécurité ultime : annule systématiquement l'action de copier */
    document.addEventListener('copy', function(e) {
        e.preventDefault();
    });
</script>
""", unsafe_allow_html=True)

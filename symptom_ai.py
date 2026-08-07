import csv
import json
import re
import unicodedata
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parent
SYMPTOM_DB_PATH = APP_ROOT / "data" / "symtoms_treatment.csv"
SPECIES_DB_PATH = APP_ROOT / "data" / "species_knowledge.json"


BRAZILIAN_STATES = {
    "acre": "Acre",
    "ac": "Acre",
    "alagoas": "Alagoas",
    "al": "Alagoas",
    "amapa": "Amapa",
    "ap": "Amapa",
    "amazonas": "Amazonas",
    "am": "Amazonas",
    "bahia": "Bahia",
    "ba": "Bahia",
    "ceara": "Ceara",
    "ce": "Ceara",
    "distrito federal": "Distrito Federal",
    "df": "Distrito Federal",
    "espirito santo": "Espirito Santo",
    "es": "Espirito Santo",
    "goias": "Goias",
    "go": "Goias",
    "maranhao": "Maranhao",
    "ma": "Maranhao",
    "mato grosso": "Mato Grosso",
    "mt": "Mato Grosso",
    "mato grosso do sul": "Mato Grosso do Sul",
    "ms": "Mato Grosso do Sul",
    "minas gerais": "Minas Gerais",
    "mg": "Minas Gerais",
    "para": "Para",
    "pa": "Para",
    "paraiba": "Paraiba",
    "pb": "Paraiba",
    "parana": "Parana",
    "pr": "Parana",
    "pernambuco": "Pernambuco",
    "pe": "Pernambuco",
    "piaui": "Piaui",
    "pi": "Piaui",
    "rio de janeiro": "Rio de Janeiro",
    "rj": "Rio de Janeiro",
    "rio grande do norte": "Rio Grande do Norte",
    "rn": "Rio Grande do Norte",
    "rio grande do sul": "Rio Grande do Sul",
    "rs": "Rio Grande do Sul",
    "rondonia": "Rondonia",
    "ro": "Rondonia",
    "roraima": "Roraima",
    "rr": "Roraima",
    "santa catarina": "Santa Catarina",
    "sc": "Santa Catarina",
    "sao paulo": "Sao Paulo",
    "sp": "Sao Paulo",
    "sergipe": "Sergipe",
    "se": "Sergipe",
    "tocantins": "Tocantins",
    "to": "Tocantins",
}


US_STATES = {
    "alabama": "Alabama",
    "alaska": "Alaska",
    "arizona": "Arizona",
    "arkansas": "Arkansas",
    "california": "California",
    "colorado": "Colorado",
    "connecticut": "Connecticut",
    "delaware": "Delaware",
    "district of columbia": "District of Columbia",
    "washington dc": "District of Columbia",
    "florida": "Florida",
    "georgia": "Georgia",
    "hawaii": "Hawaii",
    "idaho": "Idaho",
    "illinois": "Illinois",
    "indiana": "Indiana",
    "iowa": "Iowa",
    "kansas": "Kansas",
    "kentucky": "Kentucky",
    "louisiana": "Louisiana",
    "maine": "Maine",
    "maryland": "Maryland",
    "massachusetts": "Massachusetts",
    "michigan": "Michigan",
    "minnesota": "Minnesota",
    "mississippi": "Mississippi",
    "missouri": "Missouri",
    "montana": "Montana",
    "nebraska": "Nebraska",
    "nevada": "Nevada",
    "new hampshire": "New Hampshire",
    "new jersey": "New Jersey",
    "new mexico": "New Mexico",
    "new york": "New York",
    "north carolina": "North Carolina",
    "north dakota": "North Dakota",
    "ohio": "Ohio",
    "oklahoma": "Oklahoma",
    "oregon": "Oregon",
    "pennsylvania": "Pennsylvania",
    "rhode island": "Rhode Island",
    "south carolina": "South Carolina",
    "south dakota": "South Dakota",
    "tennessee": "Tennessee",
    "texas": "Texas",
    "utah": "Utah",
    "vermont": "Vermont",
    "virginia": "Virginia",
    "washington": "Washington",
    "west virginia": "West Virginia",
    "wisconsin": "Wisconsin",
    "wyoming": "Wyoming",
}


STATE_ALIASES = {**BRAZILIAN_STATES, **US_STATES}


SYMPTOM_PATTERNS = {
    "coceira": ["coceira", "cocando", "itch", "itching", "prurido"],
    "dor": ["dor", "pain", "dolorido", "ardida", "painful", "latejando", "dor intensa", "dor leve"],
    "ardor": ["ardor", "queimacao", "queima", "burning", "sting", "stinging", "queimação"],
    "inchaco": ["inchaco", "inchado", "swelling", "swollen", "edema"],
    "vermelhidao": ["vermelho", "vermelhidao", "redness", "rash", "erupcao"],
    "bolhas": ["bolha", "bolhas", "blister", "blisters"],
    "carocos": ["caroco", "carocos", "welts", "welt", "bumps", "pimples", "hives"],
    "necrose": ["necrose", "ferida preta", "pele escura", "mancha roxa"],
    "sangramento": ["sangramento", "sangrando", "sangue", "hemorragia"],
    "dormencia": ["dormencia", "dormência", "dormente", "formigamento", "formigando"],
    "nausea": ["nausea", "enjoo"],
    "vomito": ["vomito", "vomiting"],
    "febre": ["febre", "fever"],
    "calafrios": ["calafrios", "chills"],
    "falta_de_ar": ["falta de ar", "dificuldade para respirar", "difficulty breathing", "shortness of breath"],
    "dor_muscular": ["dor muscular", "muscle pain"],
    "espasmos": ["espasmo", "espasmos", "espasmos musculares"],
    "rigidez_muscular": ["rigidez muscular", "musculo travado", "musculos travados"],
    "pouca_lesao": ["pouca lesao", "pouca alteracao visual", "quase nao aparece", "lesao pequena"],
    "fraqueza": ["fraqueza", "fraco", "fraqueza muscular"],
    "tontura": ["tontura", "tonto", "desmaio"],
    "tremores": ["tremor", "tremores", "tremendo"],
    "sonolencia": ["sonolencia", "sonolência", "sonolento"],
    "palpitacoes": ["palpitacao", "palpitacoes", "palpitação", "palpitações", "taquicardia"],
    "pressao_alterada": ["pressao", "pressão", "queda de pressao", "queda de pressão", "pressao alta", "pressão alta"],
    "urina_escura": ["urina escura", "xixi escuro"],
    "visao_alterada": ["visao turva", "visão turva", "visao dupla", "visão dupla", "palpebra caída", "pálpebra caída"],
    "dificuldade_para_engolir": ["dificuldade para engolir", "dificuldade de engolir"],
    "dificuldade_para_falar": ["dificuldade para falar", "fala enrolada"],
    "dor_abdominal": ["dor abdominal", "dor na barriga", "cólica abdominal"],
    "diarreia": ["diarreia", "diarréia"],
    "caibra": ["caibra", "cramping", "cramps"],
    "dor_de_cabeca": ["dor de cabeca", "headache"],
    "ansiedade": ["ansiedade", "anxiety"],
    "suor": ["suor", "suando", "sweating"],
    "agitacao": ["agitacao", "agitação", "agitado"],
}


BITE_LOCATION_PATTERNS = {
    "braco": ["braco", "arm", "forearm"],
    "mao": ["mao", "hand", "finger", "dedo"],
    "perna": ["perna", "leg", "thigh", "coxa"],
    "pe": ["pe", "foot", "feet", "toe", "dedao do pe"],
    "tornozelo": ["tornozelo", "ankle"],
    "pescoco": ["pescoco", "neck"],
    "rosto": ["rosto", "face", "bochecha", "cheek"],
    "costas": ["costas", "back"],
    "tronco": ["tronco", "torso"],
    "barriga": ["barriga", "abdomen", "estomago", "stomach", "belly"],
    "ombro": ["ombro", "shoulder"],
    "peito": ["peito", "chest"],
}


BODY_WORDS = set(BITE_LOCATION_PATTERNS)


BUG_TRANSLATIONS = {
    "spiders": "Aranhas",
    "bed_bugs": "Percevejos",
    "chiggers": "Chiggers",
    "fire_ants": "Formigas de fogo",
    "ticks": "Carrapatos",
    "ants": "Formigas",
    "fleas": "Pulgas",
    "mosquitos": "Mosquitos",
    "no_bites": "Sem picadas",
}


SYMPTOM_LABELS = {
    "inchaco": "inchaço",
    "vermelhidao": "vermelhidão",
    "carocos": "caroços",
    "nausea": "náusea",
    "vomito": "vômito",
    "caibra": "cãibra",
    "dor_de_cabeca": "dor de cabeça",
}


BITE_LOCATION_LABELS = {
    "braco": "braço",
    "mao": "mão",
    "pe": "pé",
    "pescoco": "pescoço",
}


DISPLAY_TEXT_REPLACEMENTS = {
    "itching": "coceira",
    "itch": "coceira",
    "rash": "erupção cutânea",
    "pain": "dor",
    "muscle pain": "dor muscular",
    "cramping": "cãibra",
    "cramps": "cãibras",
    "red or purple blister": "bolha vermelha ou roxa",
    "red welt": "vergão vermelho",
    "swelling": "inchaço",
    "skin damage": "lesão na pele",
    "sweating": "suor",
    "difficulty breathing": "dificuldade para respirar",
    "headache": "dor de cabeça",
    "nausea": "náusea",
    "vomiting": "vômito",
    "fever": "febre",
    "chills": "calafrios",
    "anxiety": "ansiedade",
    "swollen lymph glands": "gânglios inchados",
    "high blood pressure": "pressão alta",
    "few days after bite to show": "pode aparecer alguns dias depois da picada",
    "possibly burning": "possível ardor",
    "possibly itching": "possível coceira",
    "can cause cellulitis": "pode causar celulite",
    "clean with soap and water": "limpar com água e sabão",
    "medical attention": "atenção médica",
    "ice pack": "compressa gelada",
    "elevate affected area": "elevar a área afetada",
    "antihistamine (benadryl)": "anti-histamínico (Benadryl)",
    "antibiotic ointment if blisters develop": "pomada antibiótica se surgirem bolhas",
    "cold cloth": "pano frio",
    "anti-itch cream": "creme contra coceira",
    "calamine lotion": "loção de calamina",
    "oral antihistamine": "anti-histamínico oral",
    "pain reliever to relieve swelling and pain": "analgésico para aliviar inchaço e dor",
    "antiseptic to welts": "antisséptico nos vergões",
    "hydrocortisone cream": "creme de hidrocortisona",
    "reddish bumps": "caroços avermelhados",
    "red welts": "vergões vermelhos",
    "pimples": "bolinhas",
    "hives": "urticária",
    "blisters": "bolhas",
    "multiple bites": "múltiplas picadas",
    "warm, moist areas": "áreas quentes e úmidas",
    "sting": "ardor",
    "half bleach, half water": "meia parte água sanitária, meia parte água",
    "diluted ammonium solution": "solução de amônio diluída",
    "aloe vera": "babosa",
    "witch hazel": "hamamelis",
    "antibiotics": "antibióticos",
    "burning": "ardor",
    "if severe": "se for grave",
    "hand": "mão",
    "arm": "braço",
    "neck": "pescoço",
    "face": "rosto",
}


TERM_DISPLAY_REPLACEMENTS = {
    "inchaco": "inchaço",
    "vermelhidao": "vermelhidão",
    "nausea": "náusea",
    "vomito": "vômito",
    "pressao": "pressão",
    "dormencia": "dormência",
    "visao": "visão",
    "palpebra": "pálpebra",
    "area": "área",
    "areas": "áreas",
    "plantacoes": "plantações",
    "regiao": "região",
    "compativel": "compatível",
    "medico": "médico",
    "medica": "médica",
    "urgencia": "urgência",
    "maxima": "máxima",
    "vitima": "vítima",
}


REGION_STATES = {
    "norte": {"acre", "amapa", "amazonas", "para", "rondonia", "roraima", "tocantins", "norte"},
    "nordeste": {"alagoas", "bahia", "ceara", "maranhao", "paraiba", "pernambuco", "piaui", "rio grande do norte", "sergipe", "nordeste"},
    "centro-oeste": {"distrito federal", "goias", "mato grosso", "mato grosso do sul", "centro oeste", "centro-oeste"},
    "sudeste": {"espirito santo", "minas gerais", "rio de janeiro", "sao paulo", "sudeste"},
    "sul": {"parana", "rio grande do sul", "santa catarina", "sul"},
    "todo o brasil": {"todo o brasil", "brasil"},
}


SPECIES_KNOWLEDGE = [
    {
        "display_name": "Loxosceles",
        "animal": "aranha_marrom",
        "popular_name": "Aranha-marrom",
        "category": "aranha",
        "type": "Aranha peçonhenta",
        "color": "marrom-claro a marrom-escuro",
        "size": "3 a 4 cm com as pernas abertas",
        "activity_period": "noite, madrugada",
        "affected_regions": ["pé", "mão", "perna", "braço"],
        "accident_sites": ["atrás de móveis", "roupas guardadas", "sapatos", "caixas", "armários", "locais escuros e secos"],
        "symptoms": ["ardência", "vermelhidão", "dor moderada", "pele arroxeada", "bolhas", "necrose", "ferida escura", "sensibilidade ao toque", "febre", "náusea", "mal-estar", "fraqueza", "dor no corpo", "necrose progressiva", "lesão escura central", "evolução lenta", "aumento gradual da dor", "pele arroxeada ao redor da lesão", "ponto único", "inchaço leve", "queimação", "dor crescente", "bolha escura central"],
        "bite_characteristics": {
            "ponto_unico": "sim",
            "duas_marcas_pequenas": "talvez",
            "vermelhidao": "moderada",
            "inchaco": "leve",
            "dor_intensa": "talvez",
            "queimacao": "sim",
            "dormencia": "talvez",
            "roxo": "sim",
            "bolha": "sim",
            "necrose": "sim",
            "sangramento": "raro",
            "ferida_central": "sim",
            "coceira": "talvez",
            "calor_local": "sim",
            "dor_crescente": "sim",
        },
        "local_signs": ["ardência", "vermelhidão", "dor moderada", "pele arroxeada", "bolhas", "necrose", "ferida escura", "sensibilidade ao toque"],
        "general_signs": ["febre", "náusea", "mal-estar", "fraqueza", "dor no corpo"],
        "specific_signs": ["necrose progressiva", "lesão escura central", "evolução lenta", "aumento gradual da dor", "pele arroxeada ao redor da lesão"],
        "pain_intensity": "Inicialmente leve a moderada; pode aumentar após horas.",
        "symptom_onset": "horas após a picada",
        "average_evolution": "24h a vários dias.",
        "risk_groups": ["crianças", "idosos", "pessoas imunossuprimidas"],
        "severity": "moderada a grave",
        "risk_level": "alto",
        "alert_signs": ["necrose progressiva", "lesão escura central", "febre", "mal-estar", "fraqueza"],
        "ai_indicators": ["necrose", "lesão arroxeada", "evolução lenta", "pouca dor inicial", "bolha escura central"],
        "differentiation": ["diferente da armadeira: dor não costuma ser imediata intensa", "diferente do escorpião: presença de necrose", "diferente da viúva-negra: poucos sintomas musculares"],
        "description": "A picada da aranha-marrom geralmente começa discreta, com pouca dor inicial. Após algumas horas, podem surgir vermelhidão, área arroxeada, bolhas e necrose progressiva, formando uma ferida escura central. Em casos moderados ou graves podem ocorrer febre, mal-estar e fraqueza.",
        "guidance": "Lavar com água e sabão, manter repouso e procurar atendimento.",
        "dont_do": "Não cortar, sugar, fazer torniquete, passar álcool, pó de café, pasta de dente ou pomadas.",
        "regions": ["paraná", "santa catarina", "rio grande do sul", "são paulo", "minas gerais", "sul", "sudeste"],
        "environment": ["atrás de móveis", "roupas guardadas", "roupas", "sapatos", "caixas", "armários", "locais escuros e secos"],
    },
    {
        "display_name": "Phoneutria",
        "animal": "armadeira",
        "popular_name": "Aranha-armadeira",
        "category": "aranha",
        "type": "Aranha peçonhenta",
        "color": "marrom ou acinzentada",
        "size": "até 15 cm com as pernas abertas",
        "activity_period": "noite",
        "behavior": "pode levantar as patas dianteiras quando ameaçada",
        "affected_regions": ["pé", "mão", "perna"],
        "accident_sites": ["bananeiras", "jardins", "quintais", "entulhos", "sapatos", "roupas", "dentro de casa", "locais escuros"],
        "symptoms": ["dor intensa imediata", "vermelhidão forte", "inchaço", "ardência", "suor local", "suor excessivo", "tremores", "agitação", "palpitações", "náusea", "dor extremamente intensa imediata", "sintomas neurológicos rápidos", "espasmos musculares", "priapismo", "agitação intensa", "duas marcas pequenas", "queimação", "formigamento", "calor local"],
        "bite_characteristics": {
            "ponto_unico": "não",
            "duas_marcas_pequenas": "sim",
            "vermelhidao": "forte",
            "inchaco": "medio",
            "dor_intensa": "sim",
            "queimacao": "sim",
            "dormencia": "talvez",
            "formigamento": "sim",
            "roxo": "raro",
            "bolha": "raro",
            "necrose": "não",
            "sangramento": "raro",
            "ferida_central": "não",
            "sensibilidade_ao_toque": "sim",
            "dor_irradiando": "talvez",
            "suor_local": "sim",
            "calor_local": "sim",
        },
        "local_signs": ["dor intensa imediata", "vermelhidão forte", "inchaço", "ardência", "suor local"],
        "general_signs": ["suor excessivo", "tremores", "agitação", "palpitações", "náusea"],
        "specific_signs": ["dor extremamente intensa imediata", "sintomas neurológicos rápidos", "espasmos musculares", "priapismo", "agitação intensa"],
        "pain_intensity": "Muito intensa imediatamente.",
        "symptom_onset": "minutos após a picada",
        "average_evolution": "Minutos a horas.",
        "risk_groups": ["crianças", "idosos"],
        "severity": "moderada a grave",
        "risk_level": "alto",
        "alert_signs": ["dor extrema", "sintomas neurológicos rápidos", "espasmos musculares", "priapismo", "agitação intensa"],
        "ai_indicators": ["dor imediata extrema", "muito suor", "tremores rápidos", "duas marcas pequenas"],
        "differentiation": ["diferente da aranha-marrom: dor imediata muito forte", "diferente do escorpião: duas marcas pequenas", "diferente da viúva-negra: mais sintomas locais intensos"],
        "description": "A picada da armadeira geralmente provoca dor extremamente intensa imediata, vermelhidão e ardência forte. Em alguns casos surgem tremores, suor excessivo, palpitações e espasmos musculares.",
        "guidance": "Lavar o local e procurar atendimento.",
        "dont_do": "Não cortar, sugar, fazer torniquete ou passar álcool.",
        "regions": ["sul", "sudeste", "centro-oeste"],
        "environment": ["bananeiras", "jardins", "quintais", "entulhos", "sapatos", "roupas", "dentro de casa", "locais escuros"],
    },
    {
        "display_name": "Latrodectus",
        "animal": "viuva_negra",
        "popular_name": "Viúva-negra",
        "category": "aranha",
        "type": "Aranha peçonhenta",
        "aliases": ["viúva negra", "latrodectus"],
        "color": "preta brilhante",
        "size": "1 a 3 cm",
        "activity_period": "noite, madrugada",
        "affected_regions": ["mão", "pé", "braço"],
        "accident_sites": ["cercas", "jardins", "madeiras", "entulhos", "áreas rurais"],
        "symptoms": ["dor moderada inicial", "ardência", "pequena vermelhidão", "sensibilidade ao toque", "dores musculares", "suor excessivo", "tremores", "ansiedade", "náusea", "palpitações", "espasmos musculares intensos", "dor abdominal forte", "rigidez muscular", "pressão no peito", "dores musculares progressivas", "ponto único", "vermelhidão leve", "inchaço leve", "queimação", "pouca lesão visível"],
        "bite_characteristics": {
            "ponto_unico": "sim",
            "duas_marcas_pequenas": "talvez",
            "vermelhidao": "leve",
            "inchaco": "leve",
            "dor_moderada": "sim",
            "queimacao": "sim",
            "dormencia": "talvez",
            "formigamento": "talvez",
            "roxo": "raro",
            "bolha": "raro",
            "necrose": "não",
            "sangramento": "raro",
            "ferida_central": "não",
            "sensibilidade_ao_toque": "sim",
            "suor_local": "talvez",
            "calor_local": "talvez",
        },
        "local_signs": ["dor moderada inicial", "ardência", "pequena vermelhidão", "sensibilidade ao toque"],
        "general_signs": ["dores musculares", "suor excessivo", "tremores", "ansiedade", "náusea", "palpitações"],
        "specific_signs": ["espasmos musculares intensos", "dor abdominal forte", "rigidez muscular", "pressão no peito", "dores musculares progressivas"],
        "pain_intensity": "Moderada inicialmente; pode aumentar bastante.",
        "symptom_onset": "30 minutos a poucas horas",
        "average_evolution": "Horas a 2 dias.",
        "risk_groups": ["crianças", "idosos", "cardíacos"],
        "severity": "moderada a grave",
        "risk_level": "alto",
        "alert_signs": ["espasmos musculares intensos", "dor abdominal forte", "rigidez muscular", "pressão no peito", "dor muscular forte"],
        "ai_indicators": ["dor muscular forte", "espasmos", "pouca lesão visível", "pressão no peito"],
        "differentiation": ["diferente da aranha-marrom: não causa necrose", "diferente do escorpião: espasmos musculares intensos", "diferente da armadeira: menos dor local intensa"],
        "description": "A picada da viúva-negra geralmente provoca poucos sinais locais, mas pode evoluir com dores musculares intensas, espasmos, rigidez muscular e sensação de pressão no peito.",
        "guidance": "Procurar atendimento rápido, manter repouso e monitorar pressão.",
        "dont_do": "Não cortar, sugar ou usar produtos caseiros.",
        "regions": ["nordeste", "centro-oeste", "litoral brasileiro", "sudeste", "sul"],
        "environment": ["cercas", "jardins", "madeiras", "entulhos", "áreas rurais"],
    },
    {
        "display_name": "Tityus serrulatus",
        "animal": "escorpiao_amarelo",
        "popular_name": "Escorpião-amarelo",
        "category": "escorpião",
        "type": "Escorpião peçonhento",
        "aliases": ["escorpião amarelo", "lacrau-amarelo", "tityus serrulatus"],
        "color": "amarelo-claro",
        "size": "6 a 7 cm",
        "activity_period": "noite, madrugada, dias quentes, períodos chuvosos",
        "affected_regions": ["pé", "mão", "dedo", "perna", "braço"],
        "accident_sites": ["entulhos", "tijolos", "telhas", "madeiras empilhadas", "quintais", "esgotos", "ralos", "banheiros", "garagens", "depósitos escuros", "áreas urbanas", "lixo acumulado", "sapatos", "roupas", "locais quentes e úmidos"],
        "symptoms": ["dor extremamente intensa", "sensação de choque elétrico", "ardência forte", "vermelhidão leve", "pequeno inchaço", "formigamento", "dormência leve", "dor irradiando pelo membro", "suor excessivo", "suor frio", "agitação", "ansiedade", "tremores", "náusea", "vômito", "palpitações", "taquicardia", "aumento da pressão arterial", "queda de pressão", "dor abdominal", "salivação excessiva", "dificuldade para respirar", "respiração acelerada", "fraqueza", "mal-estar", "sonolência", "espasmos musculares", "convulsões", "edema pulmonar", "alteração cardíaca", "ponto único", "dor intensa", "queimação", "choque local", "calor local"],
        "bite_characteristics": {
            "ponto_unico": "sim",
            "duas_marcas_pequenas": "não",
            "vermelhidao": "leve a moderada",
            "inchaco": "leve",
            "dor_intensa": "sim",
            "queimacao": "sim",
            "dormencia": "talvez",
            "formigamento": "sim",
            "roxo": "raro",
            "bolha": "raro",
            "necrose": "não",
            "sangramento": "raro",
            "ferida_central": "não",
            "sensibilidade_ao_toque": "sim",
            "dor_irradiando": "sim",
            "choque_local": "sim",
            "suor_local": "talvez",
            "calor_local": "sim",
        },
        "local_signs": ["dor extremamente intensa", "sensação de choque elétrico", "ardência forte", "vermelhidão leve", "pequeno inchaço", "formigamento", "dormência leve", "sensibilidade intensa ao toque", "calor local", "dor irradiando pelo membro"],
        "general_signs": ["suor excessivo", "suor frio", "agitação", "ansiedade", "tremores", "náusea", "vômito", "palpitações", "taquicardia", "aumento da pressão arterial", "queda de pressão", "dor abdominal", "salivação excessiva", "dificuldade para respirar", "respiração acelerada", "fraqueza", "mal-estar", "sonolência"],
        "specific_signs": ["sintomas sistêmicos rápidos", "dor desproporcional ao aspecto visual da lesão", "alteração cardíaca", "edema pulmonar", "convulsões", "sudorese intensa logo após a picada", "agitação importante poucos minutos após o acidente", "sintomas graves mais comuns em crianças", "pouco inchaço mesmo com dor extrema"],
        "pain_intensity": "Muito forte nos primeiros minutos, semelhante a choque elétrico; pode irradiar rapidamente pelo membro afetado e costuma ser desproporcional ao aspecto visual da lesão.",
        "symptom_onset": "imediato; segundos a poucos minutos após a picada",
        "average_evolution": "Sintomas locais imediatos; sintomas sistêmicos podem surgir entre 10 minutos e 3 horas.",
        "risk_groups": ["crianças", "idosos", "pessoas cardíacas", "pessoas com problemas respiratórios", "pessoas alérgicas"],
        "severity": "moderada a grave; alto potencial de complicações sistêmicas",
        "risk_level": "muito alto",
        "epidemiological_note": "Principal espécie responsável por acidentes graves no Brasil.",
        "alert_signs": ["criança picada", "suor intenso", "vômitos", "sonolência", "tremores", "dificuldade respiratória", "alteração cardíaca", "convulsões", "edema pulmonar", "piora rápida"],
        "ai_indicators": ["dor extremamente intensa com pouca alteração visual", "picada ocorrida em ambiente urbano", "sintomas sistêmicos rápidos", "sudorese intensa logo após a picada", "agitação importante", "apenas um ponto de picada visível", "pouco inchaço apesar da dor intensa", "criança com vômitos e sonolência após dor local intensa"],
        "differentiation": ["diferente da aranha-marrom: não costuma causar necrose", "diferente da armadeira: sintomas neurológicos diferentes e ausência de grandes marcas de presas", "diferente do escorpião-marrom: maior frequência de sintomas graves sistêmicos", "diferente de cobras: normalmente não causa sangramento importante nem grande edema"],
        "description": "A picada do escorpião-amarelo geralmente provoca dor extremamente intensa imediata, sensação de choque e ardência forte no local. Apesar da intensidade da dor, a lesão costuma apresentar pouca alteração visual, geralmente apenas leve vermelhidão e pequeno inchaço. Em casos moderados ou graves podem surgir suor excessivo, vômitos, tremores, palpitações, dificuldade respiratória e alterações cardíacas. Crianças possuem maior risco de complicações graves e evolução rápida.",
        "guidance": "Procurar hospital imediatamente e manter o local limpo, especialmente se a vítima for criança, idosa ou apresentar vômitos, sonolência, suor intenso ou dificuldade respiratória.",
        "dont_do": "Não cortar, sugar, fazer torniquete ou passar álcool.",
        "regions": ["são paulo", "minas gerais", "goiás", "paraná", "bahia", "pernambuco", "ceará", "tocantins", "distrito federal", "mato grosso do sul", "mato grosso", "sudeste", "sul", "centro-oeste", "nordeste", "norte"],
        "environment": ["entulhos", "tijolos", "telhas", "madeiras empilhadas", "quintais", "esgotos", "esgoto", "ralos", "banheiros", "garagens", "depósitos escuros", "áreas urbanas", "lixo acumulado", "lixo", "sapatos", "roupas", "locais quentes e úmidos"],
    },
    {
        "display_name": "Tityus bahiensis",
        "animal": "escorpiao_marrom",
        "popular_name": "Escorpião-marrom",
        "category": "escorpião",
        "type": "Escorpião peçonhento",
        "aliases": ["escorpião marrom", "escorpião-preto-marrom", "tityus bahiensis"],
        "color": "marrom-escuro",
        "size": "6 a 8 cm",
        "activity_period": "noite, madrugada, dias quentes e úmidos",
        "affected_regions": ["pé", "mão", "dedo", "perna", "braço"],
        "accident_sites": ["entulhos", "madeiras empilhadas", "tijolos", "telhas", "quintais", "ralos", "banheiros", "garagens", "depósitos escuros", "áreas rurais", "locais úmidos e escondidos", "calçados", "roupas"],
        "symptoms": ["dor intensa imediata", "sensação de choque", "ardência forte", "vermelhidão leve a moderada", "pequeno inchaço", "dormência leve", "formigamento", "sensibilidade ao toque", "calor local", "suor excessivo", "suor frio", "agitação", "ansiedade", "tremores leves", "náusea", "vômito", "palpitações", "taquicardia", "dor muscular", "fraqueza", "mal-estar", "pressão alta", "queda de pressão", "dor abdominal", "respiração acelerada", "dificuldade respiratória", "sonolência", "convulsões", "edema pulmonar", "ponto único", "queimação", "choque local"],
        "bite_characteristics": {
            "ponto_unico": "sim",
            "duas_marcas_pequenas": "não",
            "vermelhidao": "leve a moderada",
            "inchaco": "leve",
            "dor_intensa": "sim",
            "queimacao": "sim",
            "dormencia": "talvez",
            "formigamento": "sim",
            "roxo": "raro",
            "bolha": "raro",
            "necrose": "não",
            "sangramento": "raro",
            "ferida_central": "não",
            "sensibilidade_ao_toque": "sim",
            "dor_irradiando": "talvez",
            "choque_local": "sim",
            "suor_local": "talvez",
        },
        "local_signs": ["dor intensa imediata", "sensação de choque", "ardência forte", "vermelhidão leve a moderada", "pequeno inchaço", "formigamento", "dormência leve", "sensibilidade ao toque", "calor local", "dor irradiando pelo membro"],
        "general_signs": ["suor excessivo", "suor frio", "agitação", "ansiedade", "tremores leves", "náusea", "vômito", "palpitações", "taquicardia", "dor muscular", "fraqueza", "mal-estar", "pressão alta", "queda de pressão", "dor abdominal", "respiração acelerada", "dificuldade respiratória", "sonolência"],
        "specific_signs": ["dor muito forte desproporcional ao aspecto visual da lesão", "pouca alteração visual na pele", "sensação de choque elétrico", "sintomas rápidos após a picada", "sudorese intensa logo após o acidente", "apenas um ponto de picada visível", "pouca chance de necrose", "sintomas sistêmicos moderados em alguns casos"],
        "pain_intensity": "Muito forte nos primeiros minutos, com sensação semelhante a choque elétrico; pode irradiar pelo membro afetado e geralmente é maior do que o aspecto visual da lesão aparenta.",
        "symptom_onset": "imediato; segundos a poucos minutos após a picada",
        "risk_groups": ["crianças", "idosos", "pessoas com problemas cardíacos", "pessoas alérgicas"],
        "severity": "geralmente moderada; pode se tornar grave em crianças e idosos",
        "risk_level": "médio",
        "average_evolution": "Dor intensa nas primeiras horas; sintomas sistêmicos podem surgir entre 30 minutos e 3 horas.",
        "alert_signs": ["falta de ar", "suor intenso", "vômitos", "piora rápida", "sonolência", "convulsões", "edema pulmonar"],
        "ai_indicators": ["dor muito intensa com pouco inchaço", "pouca alteração visual comparada à dor", "picada ocorrida em ambiente urbano ou entulho", "suor excessivo e agitação rápidos", "apenas um ponto de picada visível", "ausência de necrose", "sensação de choque local muito forte"],
        "differentiation": ["diferente da aranha-marrom: normalmente não causa necrose", "diferente da armadeira: sintomas neurológicos menos intensos", "diferente do escorpião-amarelo: menor frequência de sintomas sistêmicos graves", "diferente de cobras: geralmente não há sangramento importante nem grande edema"],
        "description": "A picada do escorpião-marrom geralmente provoca dor intensa imediata, sensação de choque e ardência forte no local. Apesar da dor ser muito intensa, a lesão costuma apresentar pouca alteração visual, com apenas leve vermelhidão e pequeno inchaço. Em alguns casos podem surgir suor excessivo, tremores, náusea, palpitações e agitação. Crianças e idosos possuem maior risco de complicações graves.",
        "guidance": "Lavar o local e procurar atendimento médico, especialmente se houver criança, idoso, sintomas sistêmicos ou piora.",
        "dont_do": "Não cortar, sugar ou usar torniquete.",
        "regions": ["são paulo", "minas gerais", "paraná", "goiás", "mato grosso do sul", "mato grosso", "distrito federal", "sudeste", "sul", "centro-oeste", "interior do sudeste e centro-oeste"],
        "environment": ["entulhos", "madeiras empilhadas", "madeiras", "tijolos", "telhas", "quintais", "ralos", "banheiros", "garagens", "depósitos escuros", "áreas rurais", "locais úmidos e escondidos", "calçados", "roupas"],
    },
    {
        "display_name": "Bothrops jararaca",
        "animal": "jararaca",
        "popular_name": "Jararaca",
        "category": "cobra",
        "type": "Cobra peçonhenta",
        "color": "marrom com manchas",
        "size": "1 a 1,5 metro",
        "activity_period": "final da tarde, noite, madrugada",
        "aliases": ["jararaca", "bothrops", "jararaca comum"],
        "affected_regions": ["pé", "tornozelo", "perna", "mão"],
        "accident_sites": ["matas", "áreas rurais", "plantações", "pastos", "trilhas", "beiras de rios", "locais úmidos"],
        "symptoms": ["dor intensa", "grande inchaço", "vermelhidão forte", "sangramento", "bolhas", "pele arroxeada", "calor local", "edema progressivo", "náusea", "vômito", "suor frio", "fraqueza", "tontura", "queda de pressão", "mal-estar", "alteração de coagulação", "sangramentos espontâneos", "edema progressivo rápido", "necrose", "sangramento pela gengiva", "sangramento pela urina", "duas marcas profundas", "dor forte com edema crescente"],
        "bite_characteristics": {
            "ponto_unico": "não",
            "duas_marcas_pequenas": "não",
            "duas_marcas_profundas": "sim",
            "vermelhidao": "forte",
            "inchaco": "forte",
            "dor_intensa": "sim",
            "queimacao": "talvez",
            "dormencia": "talvez",
            "roxo": "sim",
            "bolha": "sim",
            "necrose": "talvez",
            "sangramento": "sim",
            "ferida_central": "não",
            "dor_irradiando": "talvez",
            "sensibilidade_ao_toque": "sim",
            "calor_local": "sim",
        },
        "local_signs": ["dor intensa", "grande inchaço", "vermelhidão forte", "sangramento", "bolhas", "pele arroxeada", "calor local", "edema progressivo"],
        "general_signs": ["náusea", "vômito", "suor frio", "fraqueza", "tontura", "queda de pressão", "mal-estar"],
        "specific_signs": ["alteração de coagulação", "sangramentos espontâneos", "edema progressivo rápido", "necrose em alguns casos", "sangramento pela gengiva ou urina", "sangramento no local da picada", "aumento do tempo de coagulação"],
        "pain_intensity": "Forte imediatamente; aumenta com o avanço do edema.",
        "symptom_onset": "minutos após a picada",
        "average_evolution": "Horas a dias.",
        "risk_groups": ["crianças", "idosos", "pessoas com dificuldade de acesso médico"],
        "severity": "grave",
        "risk_level": "muito alto",
        "alert_signs": ["sangramento importante", "sangramentos espontâneos", "alteração de coagulação", "edema progressivo rápido", "necrose"],
        "ai_indicators": ["grande inchaço rápido", "sangramento importante", "duas marcas profundas", "pele arroxeada", "dor forte com edema crescente"],
        "differentiation": ["diferente da cascavel: mais inchaço e sangramento", "diferente da coral: sintomas locais muito fortes", "diferente da surucucu: menos sintomas vagais intensos"],
        "description": "A picada da jararaca geralmente provoca dor intensa imediata, grande inchaço, vermelhidão e sangramento local. Em casos moderados ou graves podem surgir alterações de coagulação, necrose e sangramentos espontâneos. O edema costuma aumentar rapidamente nas primeiras horas.",
        "guidance": "Lavar o local, manter repouso e procurar hospital imediatamente.",
        "dont_do": "Não fazer torniquete, cortar, sugar ou correr.",
        "regions": ["sudeste", "sul", "nordeste", "centro-oeste", "mata atlântica"],
        "environment": ["matas", "áreas rurais", "plantações", "pastos", "trilhas", "beiras de rios", "locais úmidos"],
    },
    {
        "display_name": "Crotalus durissus",
        "animal": "cascavel",
        "popular_name": "Cascavel",
        "category": "cobra",
        "type": "Cobra peçonhenta",
        "color": "marrom-amarelada com desenhos escuros",
        "size": "1 a 2 metros",
        "activity_period": "final da tarde, noite",
        "behavior": "chocalho na cauda",
        "aliases": ["cascavel", "rattlesnake"],
        "affected_regions": ["pé", "perna", "mão"],
        "accident_sites": ["áreas secas", "pastos", "cerrado", "estradas rurais", "plantações"],
        "symptoms": ["dor moderada", "leve inchaço", "dormência", "formigamento", "fraqueza", "sonolência", "náusea", "visão turva", "tontura", "dificuldade para andar", "visão dupla", "urina escura", "dificuldade para abrir os olhos", "pálpebras caídas", "paralisia muscular progressiva", "insuficiência renal", "dor muscular generalizada", "alteração neuromuscular", "pouco inchaço", "fraqueza muscular progressiva"],
        "bite_characteristics": {
            "ponto_unico": "não",
            "duas_marcas_pequenas": "não",
            "duas_marcas_profundas": "sim",
            "vermelhidao": "leve",
            "inchaco": "leve",
            "dor_moderada": "sim",
            "dormencia": "sim",
            "sangramento": "raro",
            "roxo": "raro",
            "bolha": "raro",
            "necrose": "raro",
            "ferida_central": "não",
            "sensibilidade_ao_toque": "talvez",
            "calor_local": "talvez",
        },
        "local_signs": ["dor moderada", "leve inchaço", "dormência", "formigamento"],
        "general_signs": ["fraqueza", "sonolência", "náusea", "visão turva", "tontura", "dificuldade para andar"],
        "specific_signs": ["visão dupla", "urina escura", "dificuldade para abrir os olhos", "paralisia muscular progressiva", "insuficiência renal", "pálpebras caídas", "dor muscular generalizada", "alteração neuromuscular"],
        "pain_intensity": "Moderada; menor que jararaca.",
        "symptom_onset": "30 minutos a poucas horas",
        "average_evolution": "Horas a dias.",
        "risk_groups": ["crianças", "idosos", "pessoas com doença renal"],
        "severity": "grave",
        "risk_level": "muito alto",
        "alert_signs": ["visão dupla", "urina escura", "dificuldade para abrir os olhos", "paralisia muscular progressiva", "insuficiência renal"],
        "ai_indicators": ["pouco inchaço", "sintomas neurológicos fortes", "visão turva", "urina escura", "fraqueza muscular progressiva"],
        "differentiation": ["diferente da jararaca: menos edema e mais sintomas neurológicos", "diferente da coral: presença de urina escura", "diferente da surucucu: menos sintomas vagais"],
        "description": "A picada da cascavel geralmente apresenta poucos sinais locais, mas evolui com sintomas neurológicos importantes como visão turva, dificuldade para abrir os olhos, fraqueza muscular e urina escura. Em casos graves pode causar insuficiência renal e paralisia muscular.",
        "guidance": "Manter repouso e procurar hospital rapidamente.",
        "dont_do": "Não cortar, sugar ou fazer torniquete.",
        "regions": ["centro-oeste", "sudeste", "nordeste", "cerrado brasileiro"],
        "environment": ["áreas secas", "pastos", "cerrado", "estradas rurais", "plantações"],
    },
    {
        "display_name": "Micrurus",
        "animal": "coral_verdadeira",
        "popular_name": "Coral-verdadeira",
        "category": "cobra",
        "type": "Cobra peçonhenta",
        "color": "anéis vermelhos, pretos e amarelos/brancos",
        "size": "50 cm a 1 metro",
        "activity_period": "dia, final da tarde",
        "aliases": ["cobra coral", "coral verdadeira", "micrurus"],
        "affected_regions": ["mão", "pé", "dedo"],
        "accident_sites": ["matas", "jardins", "áreas rurais", "entulhos", "locais úmidos"],
        "symptoms": ["dor leve", "pequena vermelhidão", "dormência", "formigamento", "fraqueza", "visão turva", "sonolência", "dificuldade respiratória", "dificuldade para falar", "paralisia progressiva", "dificuldade para engolir", "dificuldade para respirar", "sintomas neurológicos rápidos", "queda das pálpebras", "fala enrolada", "fraqueza muscular progressiva", "paralisia respiratória", "pouca dor local"],
        "bite_characteristics": {
            "ponto_unico": "não",
            "duas_marcas_pequenas": "sim",
            "duas_marcas_profundas": "não",
            "vermelhidao": "leve",
            "inchaco": "leve",
            "dor": "leve",
            "queimacao": "talvez",
            "dormencia": "sim",
            "sangramento": "raro",
            "roxo": "raro",
            "bolha": "raro",
            "necrose": "não",
            "ferida_central": "não",
            "sensibilidade_ao_toque": "talvez",
            "calor_local": "talvez",
        },
        "local_signs": ["dor leve", "pequena vermelhidão", "dormência", "formigamento"],
        "general_signs": ["fraqueza", "visão turva", "sonolência", "dificuldade respiratória", "dificuldade para falar"],
        "specific_signs": ["paralisia progressiva", "dificuldade para engolir", "dificuldade para respirar", "sintomas neurológicos rápidos", "queda das pálpebras", "fala enrolada", "fraqueza muscular progressiva", "paralisia respiratória"],
        "pain_intensity": "Leve.",
        "symptom_onset": "30 minutos a poucas horas",
        "average_evolution": "Horas.",
        "risk_groups": ["crianças", "idosos"],
        "severity": "muito grave",
        "risk_level": "muito alto",
        "alert_signs": ["paralisia progressiva", "dificuldade para engolir", "dificuldade para respirar", "queda das pálpebras", "paralisia respiratória"],
        "ai_indicators": ["pouca dor local", "sintomas neurológicos rápidos", "dificuldade respiratória", "paralisia progressiva", "queda das pálpebras"],
        "differentiation": ["diferente da jararaca: quase sem edema", "diferente da cascavel: sintomas respiratórios muito rápidos", "diferente da surucucu: pouca alteração local"],
        "description": "A picada da coral verdadeira geralmente provoca poucos sinais locais, mas pode evoluir rapidamente com sintomas neurológicos graves, como paralisia muscular, dificuldade para respirar e dificuldade para engolir. É considerada uma das picadas mais perigosas do Brasil.",
        "guidance": "Manter calma e procurar hospital imediatamente.",
        "dont_do": "Não cortar, sugar ou fazer torniquete.",
        "regions": ["todo o brasil"],
        "environment": ["matas", "jardins", "áreas rurais", "entulhos", "locais úmidos"],
    },
    {
        "display_name": "Lachesis muta",
        "animal": "surucucu",
        "popular_name": "Surucucu",
        "category": "cobra",
        "type": "Cobra peçonhenta",
        "color": "marrom com desenhos escuros",
        "size": "até 3 metros",
        "activity_period": "noite, madrugada",
        "aliases": ["surucucu pico de jaca", "surucucu pico-de-jaca", "surucucu", "lachesis"],
        "affected_regions": ["pé", "perna", "mão"],
        "accident_sites": ["florestas", "áreas úmidas", "matas fechadas", "regiões isoladas"],
        "symptoms": ["dor intensa", "grande inchaço", "vermelhidão", "sangramento", "calor local", "edema progressivo", "vômito", "diarreia", "suor frio", "tontura", "fraqueza", "queda de pressão", "bradicardia", "hipotensão intensa", "sintomas vagais fortes", "desmaios", "edema extremamente rápido", "choque", "sintomas gastrointestinais intensos", "queda rápida da pressão", "dor extremamente intensa", "sangramento local"],
        "bite_characteristics": {
            "ponto_unico": "não",
            "duas_marcas_pequenas": "não",
            "duas_marcas_profundas": "sim",
            "vermelhidao": "forte",
            "inchaco": "forte",
            "dor_intensa": "sim",
            "queimacao": "talvez",
            "dormencia": "talvez",
            "formigamento": "talvez",
            "roxo": "sim",
            "sangramento": "sim",
            "bolha": "talvez",
            "necrose": "talvez",
            "ferida_central": "não",
            "sensibilidade_ao_toque": "sim",
            "calor_local": "sim",
        },
        "local_signs": ["dor intensa", "grande inchaço", "vermelhidão", "sangramento", "calor local", "edema progressivo"],
        "general_signs": ["vômito", "diarreia", "suor frio", "tontura", "fraqueza", "queda de pressão"],
        "specific_signs": ["bradicardia", "hipotensão intensa", "sintomas vagais fortes", "desmaios", "edema extremamente rápido", "choque", "sintomas gastrointestinais intensos", "queda rápida da pressão"],
        "pain_intensity": "Muito intensa.",
        "symptom_onset": "minutos após a picada",
        "average_evolution": "Horas a dias.",
        "risk_groups": ["crianças", "idosos", "pessoas em áreas isoladas"],
        "severity": "muito grave",
        "risk_level": "muito alto",
        "alert_signs": ["hipotensão intensa", "bradicardia", "desmaios", "choque", "edema extremamente rápido"],
        "ai_indicators": ["grande edema rápido", "queda de pressão importante", "vômitos e diarreia logo após a picada", "sangramento local", "dor extremamente intensa"],
        "differentiation": ["diferente da jararaca: mais sintomas vagais", "diferente da cascavel: mais edema e sangramento", "diferente da coral: sintomas locais muito fortes"],
        "description": "A picada da surucucu geralmente provoca dor extremamente intensa, grande inchaço e sangramento local. Também são comuns vômitos, diarreia, suor frio e queda importante da pressão arterial. É considerada uma das picadas mais graves do Brasil.",
        "guidance": "Manter repouso e procurar hospital imediatamente.",
        "dont_do": "Não cortar, sugar ou fazer torniquete.",
        "regions": ["amazônia", "mata atlântica", "norte"],
        "environment": ["florestas", "áreas úmidas", "matas fechadas", "regiões isoladas"],
    },
]


STRONG_URBAN_INDOOR_TERMS = [
    "ralo",
    "esgoto",
    "lixo",
    "dentro de casa",
    "casa",
    "banheiro",
    "cozinha",
    "area urbana",
    "urbana",
    "apartamento",
]


STRONG_RURAL_WILD_TERMS = [
    "mata",
    "matas",
    "floresta",
    "florestas",
    "vegetacao",
    "vegetacao fechada",
    "sitio",
    "plantacao",
    "plantacoes",
    "campo aberto",
    "cerrado",
    "area rural",
    "areas rurais",
]


SURUCUCU_CONTEXT_TERMS = [
    "para",
    "belem",
    "norte",
    "amazonia",
    "amazonica",
    "mata fechada",
    "matas fechadas",
    "floresta",
    "florestas",
    "vegetacao fechada",
    "sitio",
    "area isolada",
]


SURUCUCU_VISUAL_TERMS = [
    "duas perfuracoes",
    "duas marcas profundas",
    "sangramento continuo",
    "sangramento",
    "manchas escuras",
    "manchas arroxeadas",
    "arroxeadas",
    "bolhas",
    "grande inchaco",
    "inchaco importante",
    "pele muito inflamada",
]


SURUCUCU_SYSTEMIC_TERMS = [
    "suor excessivo",
    "suor frio",
    "tontura",
    "fraqueza intensa",
    "dificuldade para caminhar",
    "dor muito intensa",
]


SURUCUCU_DIFFERENTIAL_SYSTEMIC_TERMS = [
    "diarreia",
    "queda de pressao",
    "suor excessivo",
    "suor frio",
    "vomito",
    "vomitos",
    "mal-estar geral",
    "sintomas sistemicos intensos",
    "sintomas gastrointestinais",
]


SURUCUCU_DIFFERENTIAL_LOCAL_TERMS = [
    "dor intensa",
    "muito inchaco",
    "grande edema",
    "grande inchaco",
    "necrose",
]


VIUVA_MUSCLE_TERMS = [
    "dor muscular",
    "dores musculares",
    "dor nos musculos",
    "dor pelo corpo",
    "caibra",
    "caibras",
    "espasmo",
    "espasmos",
    "espasmos musculares",
    "rigidez muscular",
    "musculo travado",
    "musculos travados",
]


VIUVA_SYSTEMIC_TERMS = [
    "dor abdominal",
    "dor na barriga",
    "colica abdominal",
    "pressao no peito",
    "aperto no peito",
    "palpitacoes",
    "coracao acelerado",
    "suor excessivo",
    "tremores",
    "ansiedade",
    "nausea",
]


VIUVA_LOW_LOCAL_TERMS = [
    "pouca lesao",
    "pouca alteracao visual",
    "quase nao aparece",
    "lesao pequena",
    "ponto unico",
    "vermelhidao leve",
    "inchaco leve",
    "pouco inchaco",
    "sem necrose",
    "sem bolha",
    "sem sangramento",
]


VIUVA_INCOMPATIBLE_TERMS = [
    "dor extremamente intensa imediata",
    "dor extrema imediata",
    "choque eletrico",
    "sensacao de choque",
    "necrose",
    "ferida preta",
    "bolha escura",
    "grande inchaco",
    "sangramento",
    "duas marcas profundas",
]


PAIRWISE_DIFFERENTIAL_CLUES = {
    "aranha_marrom": {
        "armadeira": [
            "pouca dor no inicio",
            "lesao piora lentamente",
            "piora lenta",
            "evolui para necrose",
            "necrose",
            "area arroxeada",
            "centro escurecido",
            "destruicao da pele",
            "lesao cutanea importante",
        ],
        "viuva_negra": [
            "lesao cutanea importante",
            "necrose",
            "bolhas",
            "area arroxeada",
            "centro escurecido",
            "evolui lentamente",
            "piora lentamente",
            "local da picada e o principal problema",
        ],
        "escorpiao_amarelo": [
            "pouca dor no inicio",
            "piora lenta",
            "evolucao lenta",
            "necrose",
            "bolhas",
            "area arroxeada",
            "quadro localizado",
        ],
    },
    "armadeira": {
        "aranha_marrom": [
            "dor extremamente intensa imediatamente",
            "dor muito intensa imediata",
            "vermelhidao forte",
            "inchaco",
            "sintomas neurologicos rapidos",
            "suor excessivo",
            "tremores",
            "pressao alta",
            "agitacao",
            "marcas das presas",
        ],
        "viuva_negra": [
            "dor local muito intensa",
            "dor intensa imediata",
            "inchaco importante",
            "vermelhidao importante",
            "priapismo",
        ],
        "escorpiao_amarelo": [
            "vermelhidao",
            "inchaco",
            "sensacao de choque",
            "choque eletrico",
            "dor irradiando",
            "dor irradia",
            "priapismo",
        ],
    },
    "viuva_negra": {
        "aranha_marrom": [
            "pouca alteracao na pele",
            "pouca lesao visivel",
            "dores musculares intensas",
            "rigidez abdominal",
            "tremores",
            "sintomas sistemicos rapidos",
            "sintomas gerais",
        ],
        "armadeira": [
            "dor local menor",
            "dores musculares fortes pelo corpo",
            "dores musculares generalizadas",
            "rigidez abdominal",
            "caimbras",
            "caibras",
            "pouca vermelhidao local",
        ],
        "escorpiao_amarelo": [
            "dores musculares intensas",
            "rigidez abdominal",
            "pouca vermelhidao local",
            "caimbras generalizadas",
            "caibras generalizadas",
            "dor local menor",
        ],
    },
    "escorpiao_amarelo": {
        "aranha_marrom": [
            "dor muito intensa imediatamente",
            "dor intensa imediata",
            "pequeno ponto dolorido",
            "sem necrose importante",
            "sintomas sistemicos rapidos",
            "salivacao excessiva",
            "vomito",
            "suor",
        ],
        "armadeira": [
            "salivacao excessiva",
            "suor intenso",
            "vomitos",
            "vomito",
            "menos alteracao visivel na pele",
            "pouca alteracao visivel",
        ],
        "viuva_negra": [
            "dor local muito forte",
            "suor",
            "vomito",
            "salivacao excessiva",
            "agitacao",
            "evolui mais rapido em criancas",
        ],
    },
    "jararaca": {
        "cascavel": [
            "muito inchaco",
            "grande inchaco",
            "dor",
            "sangramento local",
            "necrose",
            "hemorragia",
            "sangramentos",
        ],
        "coral_verdadeira": [
            "grande reacao local",
            "dor",
            "inchaco",
            "hemorragias",
            "sangramento",
            "necrose",
        ],
        "surucucu": [
            "dor intensa",
            "inchaco",
            "necrose",
            "sangramento",
        ],
    },
    "cascavel": {
        "jararaca": [
            "pouca dor local",
            "visao dupla",
            "fraqueza muscular",
            "urina escura",
            "sintomas neurologicos",
        ],
        "coral_verdadeira": [
            "urina escura",
            "dores musculares",
            "visao turva",
            "queda das palpebras",
            "fraqueza muscular",
        ],
        "surucucu": [
            "pouco inchaco local",
            "sintomas neurologicos",
            "sintomas musculares",
            "urina escura",
        ],
    },
    "coral_verdadeira": {
        "jararaca": [
            "poucos sinais no local",
            "dificuldade para falar",
            "dificuldade para respirar",
            "paralisia muscular",
            "paralisia progressiva",
        ],
        "cascavel": [
            "paralisia progressiva",
            "paralisia respiratoria",
            "menos dor muscular",
            "dificuldade para respirar",
        ],
        "surucucu": [
            "poucos sintomas locais",
            "neurotoxica",
            "paralisia respiratoria",
            "paralisia progressiva",
        ],
    },
    "surucucu": {
        "jararaca": [
            "diarreia",
            "queda de pressao",
            "suor excessivo",
            "mal-estar geral",
            "sintomas sistemicos intensos",
        ],
        "cascavel": [
            "grande edema",
            "dor intensa",
            "sintomas hemorragicos",
            "sintomas gastrointestinais",
            "queda de pressao",
        ],
        "coral_verdadeira": [
            "dor intensa",
            "muito inchaco",
            "hemorragica",
            "inflamatoria",
            "suor excessivo",
            "vomitos",
            "queda de pressao",
        ],
    },
}


SIGN_WEIGHTS = {
    "specific_signs": 5,
    "ai_indicators": 4,
    "visual_characteristics": 4,
    "local_signs": 3,
    "general_signs": 1,
    "symptoms": 1,
}


BITE_CHARACTERISTIC_TERMS = {
    "ponto_unico": ["ponto unico", "um ponto", "ponto de picada"],
    "duas_marcas_pequenas": ["duas marcas pequenas", "duas marcas"],
    "duas_marcas_profundas": ["duas marcas profundas", "duas perfuracoes", "marcas profundas"],
    "vermelhidao": ["vermelhidao", "vermelho", "vermelha"],
    "inchaco": ["inchaco", "inchado", "edema"],
    "dor_intensa": ["dor intensa", "dor extrema", "dor forte"],
    "dor_moderada": ["dor moderada"],
    "queimacao": ["queimacao", "ardencia", "ardor"],
    "dormencia": ["dormencia", "dormente"],
    "formigamento": ["formigamento", "formigando"],
    "roxo": ["roxo", "arroxeado", "arroxeada"],
    "bolha": ["bolha", "bolhas"],
    "necrose": ["necrose", "ferida preta", "ferida escura"],
    "sangramento": ["sangramento", "sangue", "sangrando"],
    "ferida_central": ["ferida central", "lesao central"],
    "sensibilidade_ao_toque": ["sensibilidade ao toque", "sensivel ao toque"],
    "dor_irradiando": ["dor irradiando", "dor irradia"],
    "choque_local": ["choque local", "choque eletrico", "sensacao de choque"],
    "suor_local": ["suor local"],
    "calor_local": ["calor local", "quente no local"],
}


NEGATION_TERMS = ["sem", "nao", "não", "ausencia de", "ausência de"]


ANSWER_STRENGTH = {
    "yes": 1.0,
    "partial": 0.45,
    "uncertain": 0.25,
    "probably_yes": 0.5,
    "no": -0.65,
    "not_yet": -0.28,
    "probably_no": -0.3,
    "unknown": 0.0,
}


CLINICAL_FIELD_CONFIDENCE_THRESHOLD = 0.55
MAX_IDENTIFICATION_QUESTIONS = 5
MIN_DIAGNOSTIC_PRIORITY = 0.35


FIELD_TO_LEGACY_SYMPTOM = {
    "burning": "ardor",
    "tingling": "dormencia",
    "numbness": "dormencia",
    "itching": "coceira",
    "swelling": "inchaço",
    "redness": "vermelhidão",
    "purple_skin": "pele arroxeada",
    "pale_area": "região pálida",
    "blister": "bolhas",
    "bleeding": "sangramento",
    "necrosis": "necrose",
    "fang_marks": "marcas de presas",
    "local_sweating": "suor local",
    "body_sweating": "suor",
    "nausea": "náusea",
    "vomiting": "vômito",
    "diarrhea": "diarreia",
    "fever": "febre",
    "dizziness": "tontura",
    "weakness": "fraqueza",
    "fatigue": "cansaço",
    "tremors": "tremores",
    "contractions": "contrações",
    "spasms": "espasmos",
    "shortness_of_breath": "falta de ar",
    "urine_change": "urina escura",
    "blurred_vision": "visão embaçada",
    "ptosis": "pálpebra caída",
}


CLINICAL_FIELD_SPECS = {
    "time_since_bite": [
        (r"\b(?:ha|faz)\s+\d+\s*(?:minuto|minutos|hora|horas|dia|dias)\b", None, 0.9),
        (r"\b(?:menos de|mais de)?\s*\d+\s*(?:minuto|minutos|hora|horas|dia|dias)\b", None, 0.82),
        (r"\b(?:ontem|hoje|esta manha|de manha)\b", None, 0.72),
    ],
    "time_period": [
        (r"\b(?:manha|de manha|pela manha)\b", "manhã", 0.95),
        (r"\b(?:tarde|pela tarde|de tarde)\b", "tarde", 0.9),
        (r"\b(?:noite|a noite|de noite)\b", "noite", 0.9),
        (r"\b(?:madrugada|de madrugada)\b", "madrugada", 0.9),
    ],
    "initial_pain": [
        (r"\b(?:dor era|dor estava|comecou com dor|no inicio.*dor).{0,35}\b(?:fraca|leve|pouca|quase sem doer|quase nao doia)\b", "fraca", 0.94),
        (r"\b(?:comecou quase sem doer|na hora nao doeu|no inicio quase nao doia|pouca dor no inicio)\b", "fraca", 0.95),
        (r"\b(?:dor era|dor estava|comecou com dor).{0,35}\b(?:moderada|media)\b", "moderada", 0.86),
        (r"\b(?:dor era|dor estava|comecou com dor|na hora).{0,35}\b(?:forte|intensa|insuportavel|muito forte)\b", "intensa", 0.9),
    ],
    "current_pain": [
        (r"\b(?:agora|atualmente|hoje|nesse momento).{0,40}\b(?:dor|doendo).{0,30}\b(?:fraca|leve|pouca)\b", "fraca", 0.82),
        (r"\b(?:agora|atualmente|hoje|nesse momento).{0,40}\b(?:dor|doendo).{0,30}\b(?:moderada|media)\b", "moderada", 0.82),
        (r"\b(?:agora|atualmente|hoje|nesse momento|esta).{0,40}\b(?:dor|doendo|mais intensa|mais forte|muito forte|insuportavel)\b", "intensa", 0.82),
    ],
    "pain_onset": [
        (r"\b(?:dor|doeu|queimacao).{0,30}\b(?:na hora|imediata|imediatamente|logo apos|assim que)\b", "imediato", 0.9),
        (r"\b(?:na hora nao doeu|comecou depois|demorou para doer|dor apareceu depois|apos algumas horas|horas depois)\b", "tardio", 0.95),
    ],
    "pain_progression": [
        (r"\b(?:dor|doendo).{0,55}\b(?:aumentou|aumentando|piorou|piorando|mais forte|mais intensa|ficando mais forte)\b", "aumentando", 0.95),
        (r"\b(?:dor era fraca|pouca dor|quase nao doia).{0,70}\b(?:agora|depois).{0,45}\b(?:mais intensa|mais forte|piorou|aumentou)\b", "aumentando", 0.97),
        (r"\b(?:dor|doendo).{0,45}\b(?:melhorou|melhorando|diminuindo|diminuiu)\b", "melhorando", 0.88),
        (r"\b(?:dor|doendo).{0,45}\b(?:igual|estavel|nao mudou|nao esta piorando)\b", "estavel", 0.78),
    ],
    "burning": [(r"\b(?:ardencia|ardendo|queimacao|queimando|esta queimando|queima)\b", True, 0.92)],
    "tingling": [(r"\b(?:formigamento|formigando|pinicando)\b", True, 0.9)],
    "numbness": [(r"\b(?:dormencia|dormente|amortecido|sem sentir)\b", True, 0.9)],
    "itching": [(r"\b(?:coceira|cocando|prurido|pinicando)\b", True, 0.86)],
    "swelling": [(r"\b(?:inchaco|inchado|edema|inchou|inchada)\b", True, 0.9)],
    "swelling_progression": [
        (r"\b(?:inchaco|inchado|edema|area inchada).{0,55}\b(?:aumentando|aumentou|espalhando|subindo|crescendo|maior)\b", "aumentando", 0.94),
        (r"\b(?:subiu|esta subindo|espalhou|esta espalhando).{0,35}\b(?:perna|braco|membro|pe|mao)\b", "aumentando", 0.94),
        (r"\b(?:inchaco|edema).{0,45}\b(?:igual|estavel|nao esta piorando|nao aumentou)\b", "estavel", 0.75),
    ],
    "redness": [(r"\b(?:vermelho|vermelha|vermelhidao|avermelhado|avermelhada)\b", True, 0.88)],
    "purple_skin": [(r"\b(?:roxo|roxa|arroxeado|arroxeada|hematoma|ficou roxo|ficou roxa|pele roxa)\b", True, 0.95)],
    "pale_area": [(r"\b(?:palido|palida|esbranquicado|esbranquicada|branco no centro|area branca)\b", True, 0.86)],
    "blister": [(r"\b(?:bolha|bolhas|bolhinha|bolhinha pequena)\b", True, 0.95)],
    "bleeding": [(r"\b(?:sangramento|sangrando|sangue|hemorragia)\b", True, 0.9)],
    "necrosis": [(r"\b(?:necrose|pele escurecida|pele preta|ferida preta|ferida escura|escureceu)\b", True, 0.94)],
    "fang_marks": [(r"\b(?:duas marcas|duas perfuracoes|marcas de presa|presas|furos profundos)\b", True, 0.88)],
    "local_sweating": [(r"\b(?:suor local|suando no local|suor so no local|suor apenas no local)\b", True, 0.9)],
    "body_sweating": [(r"\b(?:suor pelo corpo|suor intenso|suando muito|suor frio|sudorese)\b", True, 0.86)],
    "nausea": [(r"\b(?:nausea|enjoo|enjoado|enjoada)\b", True, 0.88)],
    "vomiting": [(r"\b(?:vomito|vomitos|vomitando|vomitei|vomitou)\b", True, 0.9)],
    "diarrhea": [(r"\b(?:diarreia|dor de barriga com evacuacao)\b", True, 0.9)],
    "fever": [(r"\b(?:febre|febril|temperatura alta)\b", True, 0.9)],
    "dizziness": [(r"\b(?:tontura|tonto|tonta|vertigem|quase desmaiei)\b", True, 0.88)],
    "weakness": [(r"\b(?:fraqueza|me sinto fraco|me sinto fraca|estou fraco|estou fraca|moleza|sem forca|nao consigo ficar em pe)\b", True, 0.84)],
    "fatigue": [(r"\b(?:cansaco|cansado|cansada|fadiga|muito cansado|muito cansada|moleza)\b", True, 0.84)],
    "tremors": [(r"\b(?:tremor|tremores|tremendo|tremedeira)\b", True, 0.9)],
    "contractions": [(r"\b(?:contracao|contracoes|contraindo)\b", True, 0.88)],
    "spasms": [(r"\b(?:espasmo|espasmos|caibra|caibras|musculo travado)\b", True, 0.9)],
    "shortness_of_breath": [(r"\b(?:falta de ar|dificuldade para respirar|nao consigo respirar|respirar direito|respiracao dificil)\b", True, 0.96)],
    "urine_change": [(r"\b(?:urina escura|xixi escuro|urina avermelhada|sangue na urina|urina diferente)\b", True, 0.92)],
    "blurred_vision": [(r"\b(?:visao emba[cç]ada|visao turva|visao dupla|enxergando emba[cç]ado|dificuldade para enxergar)\b", True, 0.9)],
    "ptosis": [(r"\b(?:palpebra caida|palpebras caidas|olho caindo|dificuldade para abrir os olhos|olhos pesados)\b", True, 0.92)],
    "animal_seen": [(r"\b(?:vi o animal|vi a aranha|vi o escorpiao|vi a cobra|animal visto|consegui ver|tenho foto)\b", True, 0.9)],
    "context": [(r"\b(?:casa|quintal|jardim|mato|entulho|madeira|sapato|roupa|cama|rural|plantacao|galpao|banheiro|ralo|lixo)\b", None, 0.78)],
}


FIELD_SPECIES_WEIGHTS = {
    "pain_delayed_worsening": {"aranha_marrom": 5.0, "armadeira": -3.0, "escorpiao_amarelo": -3.0, "escorpiao_marrom": -2.0},
    "immediate_severe_pain": {"armadeira": 5.0, "escorpiao_amarelo": 4.5, "escorpiao_marrom": 3.5, "aranha_marrom": -3.5},
    "purple_skin": {"aranha_marrom": 4.5, "jararaca": 3.0, "surucucu": 2.0, "armadeira": -1.2, "escorpiao_amarelo": -1.2},
    "blister": {"aranha_marrom": 4.0, "jararaca": 2.0, "armadeira": -1.5, "escorpiao_amarelo": -1.5},
    "necrosis": {"aranha_marrom": 5.0, "jararaca": 2.0, "armadeira": -2.0, "escorpiao_amarelo": -2.0},
    "swelling_progression": {"jararaca": 4.0, "surucucu": 3.5, "aranha_marrom": 2.0, "escorpiao_amarelo": -1.5},
    "bleeding": {"jararaca": 4.5, "surucucu": 4.0, "cascavel": 1.0, "escorpiao_amarelo": -2.0, "aranha_marrom": -1.0},
    "fang_marks": {"jararaca": 3.5, "surucucu": 3.5, "coral_verdadeira": 2.0, "armadeira": 1.5},
    "local_sweating": {"armadeira": 3.0, "escorpiao_amarelo": 2.0, "viuva_negra": 1.5},
    "body_sweating": {"escorpiao_amarelo": 3.0, "surucucu": 2.5, "viuva_negra": 2.0, "armadeira": 1.5},
    "muscle_spasms": {"viuva_negra": 5.0, "escorpiao_amarelo": 2.5, "armadeira": 2.0, "aranha_marrom": -2.0},
    "tingling_numbness": {"cascavel": 3.0, "coral_verdadeira": 3.0, "escorpiao_amarelo": 2.0},
    "urine_change": {"cascavel": 4.0, "aranha_marrom": 2.0, "jararaca": 2.0},
    "systemic_gi": {"surucucu": 3.0, "escorpiao_amarelo": 3.0, "armadeira": 1.5, "aranha_marrom": 1.0},
    "shortness_of_breath": {"coral_verdadeira": 4.5, "escorpiao_amarelo": 3.0, "cascavel": 2.5},
    "neuro_ocular": {"cascavel": 4.0, "coral_verdadeira": 3.5, "jararaca": -2.0, "surucucu": -1.0},
    "weakness": {"cascavel": 2.5, "coral_verdadeira": 3.0, "escorpiao_amarelo": 1.0, "jararaca": -1.0},
}


# Pesos clinicos centralizados para revisao futura. Valores positivos indicam
# pistas a favor; valores negativos indicam evidencias contrarias moderadas.
# A escala pratica e: 1-2 complementar, 3-4 moderada, 5+ forte. Negativas ficam
# menores porque a ausencia pode ocorrer por relato incompleto ou sintoma precoce.
CLINICAL_REVIEW_WEIGHTS = {
    "aranha_marrom": {
        "positive_evidence": {
            "pain_delayed_worsening": 5.0,
            "purple_skin": 4.5,
            "blister": 4.0,
            "necrosis": 5.0,
        },
        "negative_evidence": {
            "pain_delayed_worsening": 2.0,
            "purple_skin": 1.6,
            "blister": 1.5,
            "necrosis": 1.2,
            "immediate_severe_pain": -2.0,
        },
    },
    "armadeira": {
        "positive_evidence": {
            "immediate_severe_pain": 5.0,
            "local_sweating": 3.0,
            "body_sweating": 1.5,
            "muscle_spasms": 2.0,
        },
        "negative_evidence": {
            "immediate_severe_pain": 2.4,
            "body_sweating": 1.0,
            "muscle_spasms": 0.8,
            "bleeding": -1.0,
        },
    },
    "viuva_negra": {
        "positive_evidence": {
            "muscle_spasms": 5.0,
            "body_sweating": 2.0,
            "systemic_gi": 1.2,
        },
        "negative_evidence": {
            "muscle_spasms": 2.0,
            "body_sweating": 0.8,
            "bleeding": -1.0,
        },
    },
    "escorpiao_amarelo": {
        "positive_evidence": {
            "immediate_severe_pain": 4.5,
            "body_sweating": 3.0,
            "systemic_gi": 3.0,
            "shortness_of_breath": 3.0,
        },
        "negative_evidence": {
            "immediate_severe_pain": 2.2,
            "body_sweating": 1.1,
            "systemic_gi": 1.0,
            "bleeding": -1.2,
        },
    },
    "escorpiao_marrom": {
        "positive_evidence": {
            "immediate_severe_pain": 3.5,
            "body_sweating": 1.8,
            "systemic_gi": 1.8,
        },
        "negative_evidence": {
            "immediate_severe_pain": 1.8,
            "body_sweating": 0.8,
            "bleeding": -1.0,
        },
    },
    "jararaca": {
        "positive_evidence": {
            "swelling_progression": 4.0,
            "bleeding": 4.5,
            "purple_skin": 3.0,
            "fang_marks": 3.5,
        },
        "negative_evidence": {
            "bleeding": 2.0,
            "swelling_progression": 1.6,
            "tingling_numbness": -1.0,
            "neuro_ocular": -2.0,
        },
    },
    "cascavel": {
        "positive_evidence": {
            "tingling_numbness": 3.0,
            "urine_change": 4.0,
            "neuro_ocular": 4.0,
            "weakness": 2.5,
        },
        "negative_evidence": {
            "neuro_ocular": 2.0,
            "weakness": 1.4,
            "urine_change": 1.0,
            "bleeding": -1.0,
        },
    },
    "coral_verdadeira": {
        "positive_evidence": {
            "shortness_of_breath": 4.5,
            "neuro_ocular": 3.5,
            "weakness": 3.0,
            "tingling_numbness": 3.0,
        },
        "negative_evidence": {
            "shortness_of_breath": 1.8,
            "neuro_ocular": 1.5,
            "weakness": 1.2,
            "bleeding": -1.0,
        },
    },
    "surucucu": {
        "positive_evidence": {
            "swelling_progression": 3.5,
            "bleeding": 4.0,
            "systemic_gi": 3.0,
            "body_sweating": 2.5,
        },
        "negative_evidence": {
            "bleeding": 1.8,
            "swelling_progression": 1.4,
            "systemic_gi": 1.2,
        },
    },
}


NEGATIVE_FIELD_SPECIES_WEIGHTS = {
    clue: {
        animal: weights.get("negative_evidence", {}).get(clue)
        for animal, weights in CLINICAL_REVIEW_WEIGHTS.items()
        if clue in weights.get("negative_evidence", {}) and weights.get("negative_evidence", {}).get(clue, 0) > 0
    }
    for clue in {
        clue
        for weights in CLINICAL_REVIEW_WEIGHTS.values()
        for clue, value in weights.get("negative_evidence", {}).items()
        if value > 0
    }
}


CONTRARY_PRESENT_FIELD_SPECIES_WEIGHTS = {
    clue: {
        animal: abs(value)
        for animal, weights in CLINICAL_REVIEW_WEIGHTS.items()
        for present_clue, value in weights.get("negative_evidence", {}).items()
        if present_clue == clue and value < 0
    }
    for clue in {
        clue
        for weights in CLINICAL_REVIEW_WEIGHTS.values()
        for clue, value in weights.get("negative_evidence", {}).items()
        if value < 0
    }
}


FIELD_TO_CLUE = {
    "pain_progression": "pain_delayed_worsening",
    "pain_onset": "immediate_severe_pain",
    "initial_pain": "immediate_severe_pain",
    "purple_skin": "purple_skin",
    "blister": "blister",
    "necrosis": "necrosis",
    "swelling_progression": "swelling_progression",
    "bleeding": "bleeding",
    "fang_marks": "fang_marks",
    "local_sweating": "local_sweating",
    "body_sweating": "body_sweating",
    "spasms": "muscle_spasms",
    "tremors": "muscle_spasms",
    "contractions": "muscle_spasms",
    "tingling": "tingling_numbness",
    "numbness": "tingling_numbness",
    "urine_change": "urine_change",
    "nausea": "systemic_gi",
    "vomiting": "systemic_gi",
    "diarrhea": "systemic_gi",
    "shortness_of_breath": "shortness_of_breath",
    "weakness": "weakness",
    "blurred_vision": "neuro_ocular",
    "ptosis": "neuro_ocular",
}


TIME_BUCKETS = {
    "VERY_EARLY": (0, 60),
    "EARLY": (60, 180),
    "INTERMEDIATE": (180, 720),
    "LATE": (720, 1440),
    "VERY_LATE": (1440, None),
}


SPECIES_TEMPORAL_PROFILES = {
    "aranha_marrom": {
        "early_positive": {"pain_delayed_worsening": 2.5},
        "late_positive": {"purple_skin": 2.0, "blister": 1.8, "necrosis": 2.2},
        "delayed_clues": {"purple_skin": 180, "blister": 180, "necrosis": 720},
    },
    "armadeira": {"early_positive": {"immediate_severe_pain": 2.5, "body_sweating": 1.2, "muscle_spasms": 1.0}},
    "escorpiao_amarelo": {"early_positive": {"immediate_severe_pain": 2.2, "systemic_gi": 1.4, "body_sweating": 1.4}},
    "escorpiao_marrom": {"early_positive": {"immediate_severe_pain": 1.8, "systemic_gi": 1.0}},
    "jararaca": {"early_positive": {"swelling_progression": 1.8, "bleeding": 1.4}, "delayed_clues": {"bleeding": 60}},
    "cascavel": {"late_positive": {"neuro_ocular": 2.4, "weakness": 1.8, "urine_change": 1.5}, "delayed_clues": {"urine_change": 360}},
    "coral_verdadeira": {"early_positive": {"shortness_of_breath": 2.0, "neuro_ocular": 1.7, "weakness": 1.5}},
    "surucucu": {"early_positive": {"swelling_progression": 1.5}, "late_positive": {"systemic_gi": 1.6, "bleeding": 1.4}},
}


ACCIDENT_CONTEXT_GROUPS = {
    "indoor_stored": ["casa", "quarto", "cama", "roupa", "roupas", "sapato", "calcado", "caixa", "caixas guardadas", "armario"],
    "urban_debris": ["garagem", "entulho", "telha", "telhas", "madeira", "lenha", "ralo", "banheiro", "lixo"],
    "garden_yard": ["quintal", "jardim", "terreno"],
    "wild_rural": ["mata", "trilha", "plantacao", "area rural", "rural", "pasto", "rio", "beira de rio"],
    "night": ["noite", "madrugada"],
    "day": ["manha", "tarde", "dia"],
}


CONTEXT_SPECIES_WEIGHTS = {
    "indoor_stored": {"aranha_marrom": 1.2, "escorpiao_amarelo": 0.9, "escorpiao_marrom": 0.9, "armadeira": 0.8},
    "urban_debris": {"escorpiao_amarelo": 1.2, "escorpiao_marrom": 1.2, "armadeira": 0.8},
    "garden_yard": {"armadeira": 1.0, "viuva_negra": 0.9, "escorpiao_marrom": 0.7},
    "wild_rural": {"jararaca": 1.4, "surucucu": 1.5, "cascavel": 1.2, "coral_verdadeira": 0.9},
    "night": {"aranha_marrom": 0.5, "armadeira": 0.5, "escorpiao_amarelo": 0.4},
    "day": {"cascavel": 0.3, "jararaca": 0.3},
}


QUESTION_BANK = [
    {
        "question_id": "urgent_breathing_standing",
        "target_field": "shortness_of_breath",
        "category": "urgency",
        "text": "A vitima esta com falta de ar, desmaio, confusao, convulsao ou muita dificuldade para ficar em pe?",
        "options": ["Sim", "Nao", "Nao sei"],
        "supports_yes": {},
        "supports_no": {},
        "urgency_priority": 2.0,
        "diagnostic_gain": 0.2,
        "answer_type": "single_choice",
    },
    {
        "question_id": "urgent_systemic_worsening",
        "target_field": "urgent_systemic_screen",
        "category": "urgency",
        "text": "Teve vomitos repetidos, suor intenso, sangramento importante, urina escura ou piora rapida?",
        "options": ["Sim", "Nao", "Nao sei"],
        "supports_yes": {},
        "supports_no": {},
        "urgency_priority": 1.7,
        "diagnostic_gain": 0.25,
        "answer_type": "single_choice",
    },
    {
        "question_id": "urgent_vulnerable_person",
        "target_field": "vulnerable_person",
        "category": "urgency",
        "text": "A pessoa picada e crianca pequena, idosa, gestante ou tem doenca importante?",
        "options": ["Sim", "Nao", "Nao sei"],
        "supports_yes": {},
        "supports_no": {},
        "urgency_priority": 1.4,
        "diagnostic_gain": 0.1,
        "answer_type": "single_choice",
    },
    {
        "question_id": "immediate_severe_pain",
        "target_field": "pain_onset",
        "category": "differential",
        "text": "A dor comecou na hora e ja veio muito intensa ou em queimacao forte?",
        "options": ["Sim", "Acho que sim", "Nao", "Nao sei"],
        "supports_yes": FIELD_SPECIES_WEIGHTS["immediate_severe_pain"],
        "supports_no": {"aranha_marrom": 2.0},
        "urgency_priority": 0,
        "diagnostic_gain": 0.86,
        "answer_type": "single_choice",
    },
    {
        "question_id": "pain_delayed_worsening",
        "target_field": "pain_progression",
        "category": "differential",
        "text": "A dor comecou fraca e aumentou depois de algum tempo?",
        "options": ["Sim", "Acho que sim", "Nao", "Nao sei"],
        "supports_yes": FIELD_SPECIES_WEIGHTS["pain_delayed_worsening"],
        "supports_no": {"armadeira": 1.0, "escorpiao_amarelo": 1.0},
        "urgency_priority": 0,
        "diagnostic_gain": 0.88,
        "answer_type": "single_choice",
    },
    {
        "question_id": "purple_skin",
        "target_field": "purple_skin",
        "category": "differential",
        "text": "A pele ficou roxa, arroxeada ou parecida com hematoma?",
        "options": ["Sim", "Um pouco", "Nao", "Nao sei"],
        "supports_yes": FIELD_SPECIES_WEIGHTS["purple_skin"],
        "supports_no": {"armadeira": 0.8, "escorpiao_amarelo": 0.8},
        "urgency_priority": 0,
        "diagnostic_gain": 0.74,
        "answer_type": "single_choice",
    },
    {
        "question_id": "blister",
        "target_field": "blister",
        "category": "differential",
        "text": "Apareceu bolha no centro ou perto da picada?",
        "options": ["Sim", "Um pouco", "Nao", "Nao sei"],
        "supports_yes": FIELD_SPECIES_WEIGHTS["blister"],
        "supports_no": {"armadeira": 0.6, "escorpiao_amarelo": 0.6},
        "urgency_priority": 0,
        "diagnostic_gain": 0.72,
        "answer_type": "single_choice",
    },
    {
        "question_id": "swelling_progression",
        "target_field": "swelling_progression",
        "category": "differential",
        "text": "O inchaco esta aumentando, se espalhando ou subindo pelo membro?",
        "options": ["Sim", "Um pouco", "Nao", "Nao sei"],
        "supports_yes": FIELD_SPECIES_WEIGHTS["swelling_progression"],
        "supports_no": {"escorpiao_amarelo": 0.8, "cascavel": 0.8},
        "urgency_priority": 0,
        "diagnostic_gain": 0.76,
        "answer_type": "single_choice",
    },
    {
        "question_id": "bleeding",
        "target_field": "bleeding",
        "category": "differential",
        "text": "Houve sangramento no local, na gengiva, no nariz ou na urina?",
        "options": ["Sim", "Um pouco", "Nao", "Nao sei"],
        "supports_yes": FIELD_SPECIES_WEIGHTS["bleeding"],
        "supports_no": {"escorpiao_amarelo": 0.7, "armadeira": 0.7},
        "urgency_priority": 0.3,
        "diagnostic_gain": 0.78,
        "answer_type": "single_choice",
    },
    {
        "question_id": "muscle_spasms",
        "target_field": "spasms",
        "category": "differential",
        "text": "Voce esta sentindo contracoes, caibras, tremores ou espasmos musculares?",
        "options": ["Sim", "Um pouco", "Nao", "Nao sei"],
        "supports_yes": FIELD_SPECIES_WEIGHTS["muscle_spasms"],
        "supports_no": {"aranha_marrom": 0.6},
        "urgency_priority": 0,
        "diagnostic_gain": 0.7,
        "answer_type": "single_choice",
    },
    {
        "question_id": "tingling_numbness",
        "target_field": "tingling",
        "category": "differential",
        "text": "Ha formigamento, dormencia ou sensacao de choque no local ou no membro?",
        "options": ["Sim", "Um pouco", "Nao", "Nao sei"],
        "supports_yes": FIELD_SPECIES_WEIGHTS["tingling_numbness"],
        "supports_no": {},
        "urgency_priority": 0,
        "diagnostic_gain": 0.62,
        "answer_type": "single_choice",
    },
    {
        "question_id": "neuro_ocular",
        "target_field": "blurred_vision",
        "category": "differential",
        "text": "A visao ficou embacada/dupla ou as palpebras estao pesadas ou caidas?",
        "options": ["Sim", "Um pouco", "Nao", "Nao sei"],
        "supports_yes": FIELD_SPECIES_WEIGHTS["neuro_ocular"],
        "supports_no": {"jararaca": 0.8, "surucucu": 0.6},
        "urgency_priority": 0.2,
        "diagnostic_gain": 0.82,
        "answer_type": "single_choice",
    },
    {
        "question_id": "muscle_weakness",
        "target_field": "weakness",
        "category": "differential",
        "text": "Ha fraqueza muscular, dificuldade para caminhar, falar ou manter os olhos abertos?",
        "options": ["Sim", "Um pouco", "Nao", "Nao sei"],
        "supports_yes": FIELD_SPECIES_WEIGHTS["weakness"],
        "supports_no": {"jararaca": 0.6},
        "urgency_priority": 0.2,
        "diagnostic_gain": 0.76,
        "answer_type": "single_choice",
    },
    {
        "question_id": "urine_change",
        "target_field": "urine_change",
        "category": "differential",
        "text": "A urina ficou escura, avermelhada ou diferente do normal?",
        "options": ["Sim", "Nao", "Nao sei"],
        "supports_yes": FIELD_SPECIES_WEIGHTS["urine_change"],
        "supports_no": {},
        "urgency_priority": 0.4,
        "diagnostic_gain": 0.68,
        "answer_type": "single_choice",
    },
    {
        "question_id": "accident_context",
        "target_field": "context",
        "category": "context",
        "text": "O acidente aconteceu em casa, roupa/sapato/cama, entulho/madeira, jardim ou area rural?",
        "options": ["Casa, roupa ou sapato", "Entulho, madeira ou jardim", "Area rural ou mata"],
        "supports_yes": {"aranha_marrom": 1.2, "escorpiao_amarelo": 1.2, "armadeira": 1.0, "jararaca": 0.8},
        "supports_no": {},
        "urgency_priority": 0,
        "diagnostic_gain": 0.38,
        "answer_type": "single_choice",
    },
    {
        "question_id": "animal_seen",
        "target_field": "animal_seen",
        "category": "context",
        "text": "Voce viu o animal ou conseguiu tirar foto dele?",
        "options": ["Vi o animal", "Tenho foto", "Nao vi"],
        "supports_yes": {},
        "supports_no": {},
        "urgency_priority": 0,
        "diagnostic_gain": 0.3,
        "answer_type": "single_choice",
    },
]


QUESTION_BY_ID = {question["question_id"]: question for question in QUESTION_BANK}


def normalize_text(value):
    value = value or ""
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    ascii_value = ascii_value.lower()
    return re.sub(r"\s+", " ", ascii_value).strip()


def split_evidence_sentences(text):
    return [part.strip() for part in re.split(r"[\.;\n]+", text or "") if part.strip()]


def evidence_for_match(original_text, pattern):
    normalized_sentences = [(sentence, normalize_text(sentence)) for sentence in split_evidence_sentences(original_text)]
    for original_sentence, normalized_sentence in normalized_sentences:
        if re.search(pattern, normalized_sentence):
            return original_sentence
    match = re.search(pattern, normalize_text(original_text))
    return match.group(0) if match else ""


def has_recent_negation(normalized_text, match_start):
    window = normalized_text[max(0, match_start - 18):match_start]
    return any(term in window.split()[-3:] for term in ("sem", "nao", "nunca"))


def has_time_uncertain_negation(normalized_text, match_start):
    window = normalized_text[max(0, match_start - 28):match_start]
    return any(term in window for term in ("ainda nao", "por enquanto nao", "ate agora nao"))


def clinical_status_from_value(value, confidence=None):
    if value == "partial":
        return "partial"
    if value == "unknown" or value is None:
        return "unknown"
    if value == "uncertain":
        return "uncertain"
    if value == "absent_with_time_uncertainty":
        return "absent_with_time_uncertainty"
    if value is False:
        return "absent"
    return "present"


def add_clinical_field(profile, field, value, confidence, source, evidence, question_id=None, status=None):
    status = status or clinical_status_from_value(value, confidence)
    if field in profile:
        current = profile[field]
        same_value = current.get("value") == value and current.get("status") == status
        if same_value and current.get("confidence", 0) >= confidence:
            return
        if not same_value:
            if source != "triage_answer" and current.get("source") == "triage_answer":
                return
            confidence = max(0.35, min(float(confidence), current.get("confidence", 0)) - 0.15)
            evidence = "{} | conflito com: {}".format(evidence or "", current.get("evidence", "")).strip(" |")

    if field in profile and profile[field].get("confidence", 0) >= confidence and source != "triage_answer":
        return

    entry = {
        "value": value,
        "confidence": round(float(confidence), 2),
        "source": source,
        "evidence": evidence or "",
        "status": status,
    }
    if field in profile and profile[field].get("value") != value:
        entry["conflict"] = True
    if question_id:
        entry["question_id"] = question_id
    profile[field] = entry


def extract_detailed_bite_location(report_text):
    normalized = normalize_text(report_text)
    body_aliases = [
        ("coxa", ["coxa", "thigh"]),
        ("braco", ["braco", "antebraco", "arm", "forearm"]),
        ("mao", ["mao", "dedo", "hand", "finger"]),
        ("perna", ["perna", "panturrilha", "canela", "leg"]),
        ("pe", ["pe", "dedao do pe", "foot", "toe"]),
        ("tornozelo", ["tornozelo", "ankle"]),
        ("pescoco", ["pescoco", "neck"]),
        ("rosto", ["rosto", "face", "bochecha", "cheek"]),
        ("costas", ["costas", "back"]),
        ("tronco", ["tronco", "torso"]),
        ("barriga", ["barriga", "abdomen", "estomago", "stomach", "belly"]),
        ("ombro", ["ombro", "shoulder"]),
        ("peito", ["peito", "chest"]),
    ]
    for label, aliases in body_aliases:
        for alias in aliases:
            if re.search(rf"\b{re.escape(alias)}\b", normalized):
                return label, alias
    return None, None


def extract_value_from_match(field, explicit_value, matched_text):
    if explicit_value is not None:
        return explicit_value
    if field == "time_since_bite":
        return matched_text.strip()
    if field == "context":
        return matched_text.strip()
    return True


def extract_answer_markers(report_text):
    markers = []
    marker_pattern = re.compile(
        r"question_id=([a-z0-9_]+)\s+target_field=([a-z0-9_]+)\s+answer=([a-z_]+)\s+normalized_value=([^\s\.]+)(?:\s+confidence=([0-9.]+))?",
        flags=re.IGNORECASE,
    )
    for match in marker_pattern.finditer(report_text or ""):
        markers.append(
            {
                "question_id": match.group(1),
                "target_field": match.group(2),
                "answer": match.group(3),
                "normalized_value": match.group(4).strip(),
                "evidence": match.group(0),
            }
        )
    return markers


def marker_value_for_field(field, marker):
    raw_value = normalize_text(marker.get("normalized_value"))
    answer = marker.get("answer")
    if answer == "unknown":
        return "unknown"
    if answer == "uncertain":
        return "uncertain"
    if answer == "partial":
        return "partial"
    if answer == "not_yet":
        return "absent_with_time_uncertainty"
    if raw_value in {"true", "sim"}:
        if field in {"pain_onset"}:
            return "imediato"
        if field in {"pain_progression", "swelling_progression"}:
            return "aumentando"
        return True
    if raw_value in {"false", "nao"}:
        return False
    return marker.get("normalized_value")


def extract_structured_clinical_data(report_text, source="initial_description"):
    profile = {}
    normalized = normalize_text(report_text)

    location, location_evidence = extract_detailed_bite_location(report_text)
    if location:
        add_clinical_field(profile, "bite_location", location, 0.9, source, location_evidence)

    for field, specs in CLINICAL_FIELD_SPECS.items():
        for pattern, explicit_value, confidence in specs:
            match = re.search(pattern, normalized)
            if not match:
                continue
            if explicit_value is True and has_recent_negation(normalized, match.start()):
                status = "absent_with_time_uncertainty" if has_time_uncertain_negation(normalized, match.start()) else "absent"
                value = "absent_with_time_uncertainty" if status == "absent_with_time_uncertainty" else False
                add_clinical_field(
                    profile,
                    field,
                    value,
                    confidence * 0.8,
                    source,
                    evidence_for_match(report_text, pattern),
                    status=status,
                )
                break
            value = extract_value_from_match(field, explicit_value, match.group(0))
            add_clinical_field(
                profile,
                field,
                value,
                confidence,
                source,
                evidence_for_match(report_text, pattern),
            )
            break

    for marker in extract_answer_markers(report_text):
        field = marker["target_field"]
        value = marker_value_for_field(field, marker)
        status = clinical_status_from_value(value)
        if status in {"unknown", "uncertain"}:
            confidence = 0.5 if status == "unknown" else 0.42
            add_clinical_field(profile, field, value, confidence, "triage_answer", marker["evidence"], marker["question_id"], status=status)
            continue
        confidence = 0.85 if marker["answer"] in {"yes", "no"} else 0.62
        if marker["answer"] == "partial":
            confidence = 0.62
        elif marker["answer"] == "not_yet":
            confidence = 0.58
        add_clinical_field(profile, field, value, confidence, "triage_answer", marker["evidence"], marker["question_id"], status=status)

    return profile


def clinical_field_value(profile, field):
    entry = (profile or {}).get(field) or {}
    return entry.get("value")


def clinical_field_answered(profile, field, threshold=CLINICAL_FIELD_CONFIDENCE_THRESHOLD):
    entry = (profile or {}).get(field)
    return bool(entry and entry.get("confidence", 0) >= threshold and entry.get("value") != "unknown")


def clinical_fields_answered(profile, fields, threshold=CLINICAL_FIELD_CONFIDENCE_THRESHOLD):
    return any(clinical_field_answered(profile, field, threshold) for field in fields)


def question_target_fields(question):
    target = question.get("target_field")
    equivalent_fields = {
        "pain_progression": {"pain_progression", "initial_pain", "pain_onset"},
        "pain_onset": {"pain_onset", "initial_pain", "current_pain"},
        "swelling_progression": {"swelling_progression"},
        "urgent_systemic_screen": {"vomiting", "body_sweating", "bleeding", "urine_change", "dizziness", "weakness"},
        "blurred_vision": {"blurred_vision", "ptosis"},
        "weakness": {"weakness", "fatigue"},
    }
    return equivalent_fields.get(target, {target})


def infer_clues_from_profile(clinical_profile):
    clues = set()
    if clinical_field_value(clinical_profile, "pain_progression") == "aumentando":
        clues.add("pain_delayed_worsening")
    if clinical_field_value(clinical_profile, "initial_pain") == "fraca" and clinical_field_value(clinical_profile, "pain_progression") == "aumentando":
        clues.add("pain_delayed_worsening")
    if clinical_field_value(clinical_profile, "pain_onset") == "imediato" or clinical_field_value(clinical_profile, "initial_pain") == "intensa":
        clues.add("immediate_severe_pain")
    for field, clue in (
        ("purple_skin", "purple_skin"),
        ("blister", "blister"),
        ("necrosis", "necrosis"),
        ("bleeding", "bleeding"),
        ("fang_marks", "fang_marks"),
        ("local_sweating", "local_sweating"),
        ("body_sweating", "body_sweating"),
        ("urine_change", "urine_change"),
        ("shortness_of_breath", "shortness_of_breath"),
    ):
        if clinical_field_value(clinical_profile, field) is True:
            clues.add(clue)
    if clinical_field_value(clinical_profile, "swelling_progression") == "aumentando":
        clues.add("swelling_progression")
    if clinical_field_value(clinical_profile, "spasms") is True or clinical_field_value(clinical_profile, "tremors") is True or clinical_field_value(clinical_profile, "contractions") is True:
        clues.add("muscle_spasms")
    if clinical_field_value(clinical_profile, "tingling") is True or clinical_field_value(clinical_profile, "numbness") is True:
        clues.add("tingling_numbness")
    if clinical_field_value(clinical_profile, "blurred_vision") is True or clinical_field_value(clinical_profile, "ptosis") is True:
        clues.add("neuro_ocular")
    if clinical_field_value(clinical_profile, "weakness") is True:
        clues.add("weakness")
    if clinical_field_value(clinical_profile, "nausea") is True or clinical_field_value(clinical_profile, "vomiting") is True or clinical_field_value(clinical_profile, "diarrhea") is True:
        clues.add("systemic_gi")
    return clues


def normalize_answer(answer_text):
    normalized = normalize_text(answer_text)
    if not normalized:
        return {"answer": "unknown", "normalized_value": None, "confidence": 0.0}
    if any(term in normalized for term in ("nao sei", "nao tenho certeza", "nao reparei", "n sei", "incerto")):
        return {"answer": "unknown", "normalized_value": None, "confidence": 0.0}
    if any(term in normalized for term in ("talvez", "pode ser", "nao tenho certeza mas acho")):
        return {"answer": "uncertain", "normalized_value": "uncertain", "confidence": 0.35}
    if any(term in normalized for term in ("um pouco", "mais ou menos", "levemente", "leve", "parcial", "so ao redor")):
        return {"answer": "partial", "normalized_value": "partial", "confidence": 0.55}
    if any(term in normalized for term in ("acho que sim", "provavelmente sim", "parece que sim")):
        return {"answer": "probably_yes", "normalized_value": True, "confidence": 0.6}
    if any(term in normalized for term in ("ainda nao", "por enquanto nao", "ate agora nao")):
        return {"answer": "not_yet", "normalized_value": "absent_with_time_uncertainty", "confidence": 0.55}
    if any(term in normalized for term in ("acho que nao", "provavelmente nao", "nao parece", "quase nao")):
        return {"answer": "probably_no", "normalized_value": False, "confidence": 0.45}
    if re.search(r"\bnao\b", normalized) or normalized.startswith("sem "):
        return {"answer": "no", "normalized_value": False, "confidence": 0.75}
    if any(term in normalized for term in ("sim", "esta subindo", "subiu", "comecou depois", "na hora nao doeu", "mais forte", "mais intensa", "aumentou", "piorou")):
        return {"answer": "yes", "normalized_value": True, "confidence": 0.85}
    return {"answer": "unknown", "normalized_value": None, "confidence": 0.0}


def clinical_answer_marker(question, answer_text):
    parsed = normalize_answer(answer_text)
    value = parsed["normalized_value"]
    if value is None:
        marker_value = "unknown"
    elif isinstance(value, str):
        marker_value = value
    else:
        marker_value = str(bool(value)).lower()
    return (
        "Resposta clinica: question_id={question_id} target_field={target_field} "
        "answer={answer} normalized_value={value} confidence={confidence}."
    ).format(
        question_id=question["question_id"],
        target_field=question["target_field"],
        answer=parsed["answer"],
        value=marker_value,
        confidence=parsed["confidence"],
    )


def parse_bite_time(value):
    normalized = normalize_text(value)
    if not normalized or any(term in normalized for term in ("nao sei", "n sei", "sem certeza", "desconhecido")):
        return {"minutes": None, "bucket": "UNKNOWN", "evidence": value or ""}

    if "meia hora" in normalized:
        minutes = 30
    elif re.search(r"\b1\s*hora\s*e\s*meia\b", normalized) or "uma hora e meia" in normalized:
        minutes = 90
    elif "desde ontem" in normalized or normalized == "ontem":
        minutes = 18 * 60
    else:
        minutes = None
        hour_match = re.search(r"\b(?:ha|faz|umas|uns|cerca de|aproximadamente)?\s*(\d+(?:[,.]\d+)?)\s*h(?:ora|oras)?\b", normalized)
        minute_match = re.search(r"\b(?:ha|faz|umas|uns|cerca de|aproximadamente)?\s*(\d+)\s*(?:minuto|minutos|min)\b", normalized)
        compact_hour = re.search(r"\b(\d+(?:[,.]\d+)?)h\b", normalized)
        day_match = re.search(r"\b(\d+)\s*(?:dia|dias)\b", normalized)
        if hour_match:
            minutes = int(float(hour_match.group(1).replace(",", ".")) * 60)
        elif compact_hour:
            minutes = int(float(compact_hour.group(1).replace(",", ".")) * 60)
        elif minute_match:
            minutes = int(minute_match.group(1))
        elif day_match:
            minutes = int(day_match.group(1)) * 24 * 60
        elif "hoje" in normalized or "agora" in normalized:
            minutes = 30

    if minutes is None:
        return {"minutes": None, "bucket": "UNKNOWN", "evidence": value or ""}

    for bucket, (start, end) in TIME_BUCKETS.items():
        if minutes >= start and (end is None or minutes < end):
            return {"minutes": minutes, "bucket": bucket, "evidence": value or ""}
    return {"minutes": minutes, "bucket": "UNKNOWN", "evidence": value or ""}


def bite_time_from_profile_or_report(clinical_profile, report_text):
    entry = (clinical_profile or {}).get("time_since_bite") or {}
    parsed = parse_bite_time(entry.get("value") or "")
    if parsed["bucket"] != "UNKNOWN":
        return parsed
    return parse_bite_time(report_text)


def clinical_field_status(clinical_profile, field):
    entry = (clinical_profile or {}).get(field) or {}
    return entry.get("status") or clinical_status_from_value(entry.get("value"))


def clue_statuses_from_profile(clinical_profile):
    statuses = {}
    confidence = {}
    for field, clue in FIELD_TO_CLUE.items():
        if field not in (clinical_profile or {}):
            continue
        status = clinical_field_status(clinical_profile, field)
        if clue in statuses and confidence.get(clue, 0) >= clinical_profile[field].get("confidence", 0):
            continue
        value = clinical_field_value(clinical_profile, field)
        if field == "pain_progression" and value != "aumentando" and status == "present":
            status = "absent"
        if field == "pain_onset" and value != "imediato" and status == "present":
            status = "absent"
        if field == "initial_pain" and value == "fraca":
            statuses["immediate_severe_pain"] = "absent"
            confidence["immediate_severe_pain"] = clinical_profile[field].get("confidence", 0)
            continue
        statuses[clue] = status
        confidence[clue] = clinical_profile[field].get("confidence", 0)
    return statuses


def time_penalty_multiplier(clue, bite_time):
    minutes = (bite_time or {}).get("minutes")
    if minutes is None:
        return 1.0
    earliest = min(
        (
            profile.get("delayed_clues", {}).get(clue)
            for profile in SPECIES_TEMPORAL_PROFILES.values()
            if profile.get("delayed_clues", {}).get(clue) is not None
        ),
        default=None,
    )
    if earliest is not None and minutes < earliest:
        return 0.2
    return 1.0


def score_negative_clinical_evidence(clinical_profile, species, matched_features, bite_time=None):
    animal = species.get("animal")
    score = 0.0
    for clue, status in clue_statuses_from_profile(clinical_profile).items():
        if status in {"unknown", "uncertain"}:
            continue
        if status in {"absent", "absent_with_time_uncertainty"}:
            weight = NEGATIVE_FIELD_SPECIES_WEIGHTS.get(clue, {}).get(animal, 0)
            if not weight:
                continue
            multiplier = 0.55 if status == "absent_with_time_uncertainty" else 1.0
            multiplier *= time_penalty_multiplier(clue, bite_time)
            delta = -weight * multiplier
            score += delta
            matched_features.append(f"evidencia_negativa:{clue}:{round(delta, 2)}")
        elif status == "present":
            contrary = CONTRARY_PRESENT_FIELD_SPECIES_WEIGHTS.get(clue, {}).get(animal, 0)
            if contrary:
                score -= contrary
                matched_features.append(f"evidencia_contraria:{clue}")
        elif status == "partial":
            weights = FIELD_SPECIES_WEIGHTS.get(clue, {})
            if animal in weights:
                score += weights[animal] * 0.45
                matched_features.append(f"estruturado_parcial:{clue}")
    return score


def score_temporal_evidence(clinical_profile, report_text, species, matched_features):
    bite_time = bite_time_from_profile_or_report(clinical_profile, report_text)
    minutes = bite_time.get("minutes")
    if minutes is None:
        return 0.0, ["Tempo desde a picada desconhecido; sem ajuste temporal."]

    animal = species.get("animal")
    profile = SPECIES_TEMPORAL_PROFILES.get(animal, {})
    statuses = clue_statuses_from_profile(clinical_profile)
    score = 0.0
    explanations = []
    early = minutes < 180

    for clue, weight in (profile.get("early_positive") or {}).items():
        if statuses.get(clue) in {"present", "partial"} and early:
            factor = 1.0 if statuses[clue] == "present" else 0.45
            score += weight * factor
            matched_features.append(f"tempo:{clue}")
            explanations.append(f"{prettify_term(clue.replace('_', ' '))} em {minutes} minutos e compativel com evolucao de {animal}.")

    for clue, weight in (profile.get("late_positive") or {}).items():
        if statuses.get(clue) in {"present", "partial"} and minutes >= 180:
            factor = 1.0 if statuses[clue] == "present" else 0.45
            score += weight * factor
            matched_features.append(f"tempo:{clue}")
            explanations.append(f"{prettify_term(clue.replace('_', ' '))} apos varias horas e compativel com evolucao de {animal}.")

    for clue, expected_min in (profile.get("delayed_clues") or {}).items():
        if statuses.get(clue) in {"absent", "absent_with_time_uncertainty"} and minutes < expected_min:
            explanations.append(f"Ausencia de {prettify_term(clue.replace('_', ' '))} apos {minutes} minutos nao reduz significativamente {animal}.")

    return score, explanations


def extract_accident_context(report_text):
    normalized = normalize_text(report_text)
    contexts = []
    for context_name, terms in ACCIDENT_CONTEXT_GROUPS.items():
        if any(term in normalized for term in terms):
            contexts.append(context_name)
    return contexts


def score_accident_context(report_text, species, matched_features):
    animal = species.get("animal")
    score = 0.0
    for context_name in extract_accident_context(report_text):
        weight = CONTEXT_SPECIES_WEIGHTS.get(context_name, {}).get(animal, 0)
        if weight:
            score += weight
            matched_features.append(f"contexto_acidente:{context_name}")
    return score


def score_structured_clues(clinical_profile, species, matched_features):
    animal = species.get("animal")
    score = 0.0
    counted_clues = set()
    for clue in infer_clues_from_profile(clinical_profile):
        weights = FIELD_SPECIES_WEIGHTS.get(clue, {})
        if animal in weights:
            score += weights[animal]
            counted_clues.add(clue)
            matched_features.append(f"estruturado:{clue}")

    if (
        clinical_field_value(clinical_profile, "initial_pain") == "fraca"
        and clinical_field_value(clinical_profile, "pain_progression") == "aumentando"
        and clinical_field_value(clinical_profile, "purple_skin") is True
        and clinical_field_value(clinical_profile, "blister") is True
        and animal == "aranha_marrom"
    ):
        score += 6.0
        matched_features.append("combinacao: dor tardia, pele arroxeada e bolha")

    return score, counted_clues


def score_question_answer_markers(report_text, species, matched_features):
    animal = species.get("animal")
    score = 0.0
    used_questions = set()
    for marker in extract_answer_markers(report_text):
        question_id = marker["question_id"]
        if question_id in used_questions:
            continue
        used_questions.add(question_id)
        question = QUESTION_BY_ID.get(question_id)
        if not question:
            continue
        strength = ANSWER_STRENGTH.get(marker.get("answer"), 0.0)
        if strength == 0:
            matched_features.append(f"resposta neutra:{question_id}")
            continue
        if strength > 0:
            weights = question.get("supports_yes") or {}
        else:
            supports_no = question.get("supports_no") or {}
            weights = supports_no if animal in supports_no else question.get("supports_yes") or {}
        if not weights or animal not in weights:
            continue
        if strength < 0 and weights is question.get("supports_yes"):
            delta = abs(weights[animal]) * strength
        else:
            delta = weights[animal] * abs(strength)
        score += delta
        matched_features.append(f"resposta:{question_id}:{marker.get('answer')}")
    return score


def apply_structured_scores_to_matches(matches, clinical_profile, report_text):
    ranking_log = []
    adjusted = []
    species_by_animal = {item.get("animal"): item for item in load_species_knowledge()}
    existing_animals = {match.get("animal") for match in matches}

    for match in matches:
        species = species_by_animal.get(match.get("animal"), match)
        matched_features = match.setdefault("matched_features", [])
        structured_score, _counted = score_structured_clues(clinical_profile, species, matched_features)
        answer_score = score_question_answer_markers(report_text, species, matched_features)
        delta = structured_score + answer_score
        if delta:
            before = match.get("score", 0)
            match["score"] = round(before + delta, 2)
            ranking_log.append({"animal": match.get("animal"), "before": before, "delta": round(delta, 2), "after": match["score"]})
        adjusted.append(match)

    for species in load_species_knowledge():
        animal = species.get("animal")
        if animal in existing_animals:
            continue
        matched_features = []
        structured_score, _counted = score_structured_clues(clinical_profile, species, matched_features)
        answer_score = score_question_answer_markers(report_text, species, matched_features)
        score = structured_score + answer_score
        if score <= 0:
            continue
        adjusted.append(
            {
                "display_name": species["display_name"],
                "animal": animal,
                "popular_name": species["popular_name"],
                "category": species["category"],
                "severity": species["severity"],
                "risk_level": species.get("risk_level", ""),
                "guidance": species["guidance"],
                "dont_do": species.get("dont_do", ""),
                "alert_signs": ", ".join(species.get("alert_signs", [])),
                "symptom_onset": species.get("symptom_onset", ""),
                "regions": ", ".join(species["regions"]),
                "environment": ", ".join(species["environment"]),
                "symptoms_reference": ", ".join(species["symptoms"]),
                "score": round(score, 2),
                "matched_features": matched_features,
            }
        )
        ranking_log.append({"animal": animal, "before": 0, "delta": round(score, 2), "after": round(score, 2)})

    adjusted.sort(key=lambda item: (-item.get("score", 0), -risk_sort_value(item), item.get("display_name", "")))
    return adjusted[:5], ranking_log


def tokenize_terms(phrases):
    terms = set()
    for phrase in phrases:
        normalized = normalize_text(phrase)
        if normalized:
            terms.add(normalized)
            if normalized.endswith("s"):
                terms.add(normalized[:-1])
            for part in [item.strip() for item in normalized.split(",")]:
                if part:
                    terms.add(part)
                    if part.endswith("s"):
                        terms.add(part[:-1])
    return sorted(terms, key=len, reverse=True)


def state_matches_region(state, region_name):
    normalized_state = normalize_text(state)
    if normalized_state == normalize_text(region_name):
        return True
    return normalized_state in REGION_STATES.get(region_name, set())


def contains_any_term(text, terms):
    return any(term in text for term in terms)


def term_in_text(text, term):
    if not term:
        return False
    pattern = r"(?<!\w){}(?!\w)".format(re.escape(term))
    return re.search(pattern, text) is not None


def report_has_positive_term(normalized_report, term):
    if not term or not term_in_text(normalized_report, term):
        return False

    for negation in NEGATION_TERMS:
        negated = f"{normalize_text(negation)} {term}"
        if term_in_text(normalized_report, negated):
            return False
    return True


def report_has_negated_term(normalized_report, term):
    if not term:
        return False

    for negation in NEGATION_TERMS:
        negated = f"{normalize_text(negation)} {term}"
        if term_in_text(normalized_report, negated):
            return True
    return False


def add_weighted_sign_score(normalized_report, species, field_name, weight, matched_features, counted_terms):
    score = 0
    for sign in tokenize_terms(species.get(field_name, [])):
        if sign and report_has_positive_term(normalized_report, sign):
            score += weight
            counted_terms.add(sign)
            matched_features.append(f"{field_name}:{sign}")
    return score


def score_visual_profile(normalized_report, species, matched_features, counted_terms):
    score = 0
    profile = species.get("visual_profile") or {}

    for field_name, value in profile.items():
        if field_name == "key_visual_clues":
            continue

        for term in tokenize_terms([value]):
            if term and term not in counted_terms and report_has_positive_term(normalized_report, term):
                score += 3
                counted_terms.add(term)
                matched_features.append(f"visual_profile:{field_name}:{term}")

    return score


def score_differential_profile(normalized_report, species, matched_features, counted_terms):
    score = 0
    for term in tokenize_terms(species.get("differential_clues", [])):
        if term and term not in counted_terms and report_has_positive_term(normalized_report, term):
            score += 2
            counted_terms.add(term)
            matched_features.append(f"perfil_diferencial:{term}")

    for term in tokenize_terms(species.get("uncommon_findings", [])):
        if term and report_has_positive_term(normalized_report, term):
            score -= 3
            matched_features.append(f"incomum:{term}")

    return score


def score_bite_characteristics(normalized_report, species, matched_features):
    score = 0
    characteristics = species.get("bite_characteristics") or {}

    for key, terms in BITE_CHARACTERISTIC_TERMS.items():
        normalized_terms = tokenize_terms(terms)
        positive_hit = any(report_has_positive_term(normalized_report, term) for term in normalized_terms)
        negated_hit = any(report_has_negated_term(normalized_report, term) for term in normalized_terms)
        if not positive_hit and not negated_hit:
            continue

        value = normalize_text(str(characteristics.get(key, "")))
        if value == "sim":
            if positive_hit:
                score += 3
                matched_features.append(f"caracteristica:{key}")
            elif negated_hit:
                score -= 3
                matched_features.append(f"incompativel:{key}")
        elif value == "nao":
            if positive_hit:
                score -= 6
                matched_features.append(f"incompativel:{key}")
            elif negated_hit:
                score += 2
                matched_features.append(f"ausencia:{key}")
        elif value == "raro":
            if positive_hit:
                score -= 3
                matched_features.append(f"raro:{key}")
            elif negated_hit:
                score += 1
                matched_features.append(f"ausencia:{key}")
        elif value == "talvez":
            if positive_hit:
                score += 1
                matched_features.append(f"possivel:{key}")

    return score


def count_term_hits(normalized_report, terms):
    return sum(1 for term in tokenize_terms(terms) if report_has_positive_term(normalized_report, term))


def score_viuva_negra_cluster(normalized_report, species, matched_features):
    muscle_hits = count_term_hits(normalized_report, VIUVA_MUSCLE_TERMS)
    systemic_hits = count_term_hits(normalized_report, VIUVA_SYSTEMIC_TERMS)
    low_local_hits = count_term_hits(normalized_report, VIUVA_LOW_LOCAL_TERMS)
    incompatible_hits = count_term_hits(normalized_report, VIUVA_INCOMPATIBLE_TERMS)
    has_viuva_cluster = muscle_hits >= 1 and (systemic_hits >= 1 or low_local_hits >= 1)

    if species.get("animal") != "viuva_negra":
        if has_viuva_cluster and species.get("animal") in {"armadeira", "escorpiao_amarelo", "escorpiao_marrom"}:
            matched_features.append("perfil menos compativel que viuva-negra")
            return -5
        return 0

    score = 0
    if muscle_hits:
        score += min(12, muscle_hits * 4)
        matched_features.append("conjunto viuva-negra: sintomas musculares")
    if systemic_hits:
        score += min(8, systemic_hits * 2)
        matched_features.append("conjunto viuva-negra: sintomas sistemicos")
    if low_local_hits:
        score += min(8, low_local_hits * 3)
        matched_features.append("conjunto viuva-negra: pouca lesao local")
    if has_viuva_cluster:
        score += 10
        matched_features.append("conjunto tipico de viuva-negra")
    if incompatible_hits:
        score -= min(12, incompatible_hits * 4)
        matched_features.append("sinais menos tipicos de viuva-negra")

    return score


def score_surucucu_differential_cluster(normalized_report, species, matched_features):
    systemic_hits = count_term_hits(normalized_report, SURUCUCU_DIFFERENTIAL_SYSTEMIC_TERMS)
    local_hits = count_term_hits(normalized_report, SURUCUCU_DIFFERENTIAL_LOCAL_TERMS)
    has_surucucu_cluster = systemic_hits >= 2 and local_hits >= 1

    if species.get("animal") != "surucucu":
        if has_surucucu_cluster and species.get("animal") == "jararaca":
            matched_features.append("perfil menos compativel que surucucu")
            return -6
        return 0

    score = 0
    if systemic_hits:
        score += min(12, systemic_hits * 3)
        matched_features.append("conjunto surucucu: sintomas sistemicos intensos")
    if local_hits:
        score += min(8, local_hits * 2)
        matched_features.append("conjunto surucucu: dor e edema importantes")
    if has_surucucu_cluster:
        score += 10
        matched_features.append("conjunto tipico de surucucu")

    return score


def score_pairwise_differential_clues(normalized_report, species, matched_features):
    animal = species.get("animal")
    pair_rules = PAIRWISE_DIFFERENTIAL_CLUES.get(animal, {})
    score = 0

    for compared_animal, clues in pair_rules.items():
        hits = [
            term
            for term in tokenize_terms(clues)
            if report_has_positive_term(normalized_report, term)
        ]
        if not hits:
            continue

        for term in hits[:4]:
            matched_features.append(f"diferencial:{compared_animal}:{term}")
        score += min(12, len(hits) * 3)

    return score


def risk_sort_value(item):
    risk_text = normalize_text(item.get("risk_level") or item.get("severity"))
    if "muito alto" in risk_text or "muito grave" in risk_text:
        return 3
    if "alto" in risk_text or "grave" in risk_text:
        return 2
    if "medio" in risk_text or "moderada" in risk_text:
        return 1
    return 0


def translate_display_text(text):
    if not text:
        return ""

    translated = normalize_text(text)
    for english in sorted(DISPLAY_TEXT_REPLACEMENTS, key=len, reverse=True):
        translated = translated.replace(english, DISPLAY_TEXT_REPLACEMENTS[english])
    return translated


def prettify_term(term):
    words = (term or "").split()
    return " ".join(TERM_DISPLAY_REPLACEMENTS.get(word, word) for word in words)


def translate_bug_name(bug_name):
    return BUG_TRANSLATIONS.get(bug_name, bug_name.replace("_", " ").capitalize())


def load_bug_knowledge():
    rows = []
    with SYMPTOM_DB_PATH.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            rows.append(row)
    return rows


def load_species_knowledge():
    if not SPECIES_DB_PATH.exists():
        return SPECIES_KNOWLEDGE

    try:
        with SPECIES_DB_PATH.open("r", encoding="utf-8") as json_file:
            species_rows = json.load(json_file)
    except (OSError, json.JSONDecodeError):
        return SPECIES_KNOWLEDGE

    if not isinstance(species_rows, list):
        return SPECIES_KNOWLEDGE

    return species_rows


def extract_symptoms(report):
    normalized = normalize_text(report)
    found = []
    for symptom, patterns in SYMPTOM_PATTERNS.items():
        if any(pattern in normalized for pattern in patterns):
            found.append(SYMPTOM_LABELS.get(symptom, symptom))
    clinical_profile = extract_structured_clinical_data(report)
    for field, label in FIELD_TO_LEGACY_SYMPTOM.items():
        if clinical_field_value(clinical_profile, field) is True and label not in found:
            found.append(label)
    return found


def extract_bite_location(report):
    normalized = normalize_text(report)
    explicit_patterns = [
        r"(?:picada|mordida|bite|bites|sting|ferida)\s+(?:no|na|nos|nas|em|on|in)?\s*([a-z\s]+?)(?=[\.,;]|$)",
        r"(?:local da picada|bite location)\s*[:\-]?\s*([a-z\s]+?)(?=[\.,;]|$)",
    ]

    for pattern in explicit_patterns:
        match = re.search(pattern, normalized)
        if match:
            chunk = match.group(1).strip()
            for label, aliases in BITE_LOCATION_PATTERNS.items():
                if any(alias in chunk for alias in aliases):
                    return label

    for label, aliases in BITE_LOCATION_PATTERNS.items():
        if any(re.search(rf"\b{re.escape(alias)}\b", normalized) for alias in aliases):
            return label

    return None


def extract_state(report):
    normalized = normalize_text(report)
    for alias in sorted(STATE_ALIASES, key=len, reverse=True):
        if re.search(rf"\b{re.escape(alias)}\b", normalized):
            return STATE_ALIASES[alias]
    return None


def clean_city_candidate(candidate):
    candidate = candidate.strip(" ,.-")
    candidate = re.sub(r"\b(estado|state|com|and|where|que|with|no|na|em)$", "", candidate, flags=re.IGNORECASE).strip(" ,.-")
    if not candidate:
        return None

    normalized = normalize_text(candidate)
    if normalized in STATE_ALIASES:
        return None
    if normalized in BODY_WORDS:
        return None
    return candidate.title()


def extract_city(report, state=None):
    patterns = [
        r"(?:cidade|city)\s+(?:de\s+)?([A-Za-zÀ-ÿ'\- ]{2,60})",
        r"(?:moro em|sou de|resido em|estou em|i live in|i am from|from)\s+([A-Za-zÀ-ÿ'\- ]{2,60})",
    ]

    for pattern in patterns:
        match = re.search(pattern, report, flags=re.IGNORECASE)
        if match:
            candidate = clean_city_candidate(match.group(1))
            if candidate:
                if state and candidate.endswith(state):
                    candidate = candidate[: -len(state)].strip(" ,-/")
                return candidate

    if state:
        state_pattern = re.escape(state)
        compact_match = re.search(rf"([A-Za-zÀ-ÿ'\- ]{{2,60}})\s*(?:,|/|-)\s*{state_pattern}", report, flags=re.IGNORECASE)
        if compact_match:
            return clean_city_candidate(compact_match.group(1))

    return None


def extract_region(report, state=None):
    normalized = normalize_text(report)
    if state:
        for region_name in REGION_STATES:
            if state_matches_region(state, region_name):
                return region_name

    for region_name in REGION_STATES:
        if region_name in normalized:
            return region_name
    return None


def match_text_score(report_text, row):
    normalized_report = normalize_text(report_text)
    row_symptoms = normalize_text(row.get("Symptoms", ""))
    row_look = normalize_text(row.get("Look", ""))
    row_location = normalize_text(row.get("Location", ""))

    score = 0
    matched_features = []

    for symptom, patterns in SYMPTOM_PATTERNS.items():
        if any(pattern in normalized_report for pattern in patterns):
            if any(pattern in row_symptoms or pattern in row_look for pattern in patterns):
                score += 2
                matched_features.append(symptom)

    bite_location = extract_bite_location(report_text)
    if bite_location:
        for alias in BITE_LOCATION_PATTERNS.get(bite_location, []):
            if alias in row_location:
                score += 1
                matched_features.append(f"local:{bite_location}")
                break

    return score, matched_features


def rank_possible_bugs(report_text):
    ranked = []
    for row in load_bug_knowledge():
        score, matched_features = match_text_score(report_text, row)
        if score <= 0:
            continue
        ranked.append(
            {
                "bug": row.get("Bug", ""),
                "bug_pt": translate_bug_name(row.get("Bug", "")),
                "score": score,
                "matched_features": matched_features,
                "symptoms_reference": translate_display_text(row.get("Symptoms", "")),
                "treatment": translate_display_text(row.get("Treatment", "")),
                "look": translate_display_text(row.get("Look", "")),
                "location_reference": translate_display_text(row.get("Location", "")),
                "resource": row.get("Resource", ""),
            }
        )

    ranked.sort(key=lambda item: (-item["score"], item["bug"]))
    return ranked[:3]


def rank_specific_species(report_text, state=None, clinical_profile=None):
    normalized_report = normalize_text(report_text)
    ranked = []
    detected_region = extract_region(report_text, state=state)
    clinical_profile = clinical_profile or extract_structured_clinical_data(report_text)

    for species in load_species_knowledge():
        score = 0
        matched_features = []
        counted_terms = set()
        environment_hit = False

        for field_name in ("specific_signs", "ai_indicators", "visual_characteristics", "local_signs", "general_signs"):
            score += add_weighted_sign_score(
                normalized_report,
                species,
                field_name,
                SIGN_WEIGHTS[field_name],
                matched_features,
                counted_terms,
            )

        score += score_visual_profile(normalized_report, species, matched_features, counted_terms)
        score += score_differential_profile(normalized_report, species, matched_features, counted_terms)

        for symptom in tokenize_terms(species["symptoms"]):
            if symptom and symptom not in counted_terms and report_has_positive_term(normalized_report, symptom):
                score += SIGN_WEIGHTS["symptoms"]
                matched_features.append(f"sintoma:{symptom}")

        for environment in tokenize_terms(species["environment"]):
            if environment and report_has_positive_term(normalized_report, environment):
                score += 3
                environment_hit = True
                matched_features.append(f"ambiente:{environment}")

        for affected_region in tokenize_terms(species.get("affected_regions", [])):
            if affected_region and report_has_positive_term(normalized_report, affected_region):
                score += 1
                matched_features.append(f"local:{affected_region}")

        for accident_site in tokenize_terms(species.get("accident_sites", [])):
            if accident_site and report_has_positive_term(normalized_report, accident_site):
                score += 2
                matched_features.append(f"contexto:{accident_site}")

        score += score_bite_characteristics(normalized_report, species, matched_features)
        score += score_pairwise_differential_clues(normalized_report, species, matched_features)
        score += score_surucucu_differential_cluster(normalized_report, species, matched_features)

        if state:
            for region_name in species["regions"]:
                if region_name == "todo o brasil" or state_matches_region(state, region_name):
                    score += 2
                    matched_features.append(f"regiao:{region_name}")
                    break
        elif detected_region and detected_region in species["regions"]:
            score += 1
            matched_features.append(f"regiao:{detected_region}")

        aliases = species.get("aliases") or []
        name_terms = [species.get("display_name", ""), species.get("popular_name", "")] + aliases
        if any(normalize_text(name_term) in normalized_report for name_term in name_terms if name_term):
            score += 4
            matched_features.append("nome citado")

        animal = species.get("animal", "")
        positive_answer_marker = normalize_text(f"resposta a favor de {animal}:")
        negative_answer_marker = normalize_text(f"resposta contra {animal}:")
        if positive_answer_marker in normalized_report:
            score += 6
            matched_features.append("resposta especifica favoravel")
        if negative_answer_marker in normalized_report:
            score -= 8
            matched_features.append("resposta especifica contraria")

        # Penalidades fortes para contexto muito incompatível.
        if contains_any_term(normalized_report, STRONG_URBAN_INDOOR_TERMS):
            if species["category"] == "cobra":
                score -= 8
            elif species["display_name"].startswith("Phoneutria") and not environment_hit:
                score -= 5
            elif species["display_name"] == "Lachesis muta":
                score -= 10

        if contains_any_term(normalized_report, STRONG_RURAL_WILD_TERMS):
            if species["display_name"] == "Tityus serrulatus" and not environment_hit:
                score -= 3

        if species.get("animal") == "surucucu":
            context_hits = sum(1 for term in SURUCUCU_CONTEXT_TERMS if term in normalized_report)
            visual_hits = sum(1 for term in SURUCUCU_VISUAL_TERMS if term in normalized_report)
            systemic_hits = sum(1 for term in SURUCUCU_SYSTEMIC_TERMS if term in normalized_report)
            if context_hits and visual_hits >= 2:
                score += 12
                matched_features.append("conjunto típico de surucucu")
            if context_hits and visual_hits >= 2 and systemic_hits:
                score += 8
                matched_features.append("contexto amazônico com sinais locais e sistêmicos")

        # Cobras precisam de sinais mais característicos ou contexto compatível.
        score += score_viuva_negra_cluster(normalized_report, species, matched_features)
        structured_score, _counted_structured = score_structured_clues(clinical_profile, species, matched_features)
        score += structured_score
        score += score_question_answer_markers(report_text, species, matched_features)
        bite_time = bite_time_from_profile_or_report(clinical_profile, report_text)
        score += score_negative_clinical_evidence(clinical_profile, species, matched_features, bite_time)
        temporal_score, temporal_explanations = score_temporal_evidence(clinical_profile, report_text, species, matched_features)
        score += temporal_score
        score += score_accident_context(report_text, species, matched_features)

        if species["category"] == "cobra":
            snake_signal_terms = tokenize_terms(species["symptoms"]) + tokenize_terms(species["environment"])
            if not any(term in normalized_report for term in snake_signal_terms):
                score -= 4

        if score <= 0:
            continue

        ranked.append(
            {
                "display_name": species["display_name"],
                "animal": species.get("animal", ""),
                "popular_name": species["popular_name"],
                "category": species["category"],
                "severity": species["severity"],
                "risk_level": species.get("risk_level", ""),
                "guidance": species["guidance"],
                "dont_do": species.get("dont_do", ""),
                "alert_signs": ", ".join(species.get("alert_signs", [])),
                "symptom_onset": species.get("symptom_onset", ""),
                "evolution": species.get("evolution", ""),
                "color": species.get("color", ""),
                "size": species.get("size", ""),
                "activity_period": species.get("activity_period", ""),
                "behavior": species.get("behavior", ""),
                "visual_profile": species.get("visual_profile", {}),
                "differential_profile": species.get("differential_profile", {}),
                "confusion_note": species.get("confusion_note", ""),
                "affected_regions": ", ".join(species.get("affected_regions", [])),
                "accident_sites": ", ".join(species.get("accident_sites", [])),
                "regions": ", ".join(species["regions"]),
                "environment": ", ".join(species["environment"]),
                "symptoms_reference": ", ".join(species["symptoms"]),
                "score": score,
                "matched_features": matched_features,
                "temporal_explanations": temporal_explanations,
            }
        )

    ranked.sort(key=lambda item: (-item["score"], -risk_sort_value(item), item["display_name"]))
    top_matches = ranked[:5]
    if not top_matches:
        return top_matches

    if len(top_matches) == 1:
        top_matches[0]["probability"] = 96

    else:
        # Amplifica diferenças entre scores para refletir melhor quando
        # uma espécie é muito mais compatível que as demais.
        weighted_scores = [max(1, item["score"]) ** 3 for item in top_matches]
        total_weight = sum(weighted_scores)
        raw_probabilities = [(weight / total_weight) * 100 if total_weight else 0 for weight in weighted_scores]
        probabilities = [int(round(value)) for value in raw_probabilities]

        diff = 100 - sum(probabilities)
        order = sorted(range(len(raw_probabilities)), key=lambda idx: raw_probabilities[idx] - probabilities[idx], reverse=(diff > 0))
        for idx in order[: abs(diff)]:
            probabilities[idx] += 1 if diff > 0 else -1

        for idx in range(1, len(probabilities)):
            if probabilities[idx] >= probabilities[idx - 1]:
                probabilities[idx] = max(1, probabilities[idx - 1] - 1)
        adjust_final = 100 - sum(probabilities)
        probabilities[-1] += adjust_final
        if len(probabilities) > 1 and probabilities[0] > 98:
            excess = probabilities[0] - 98
            probabilities[0] = 98
            probabilities[1] += excess

        for index, item in enumerate(top_matches):
            item["probability"] = probabilities[index]

    for item in top_matches:
        reasons = []
        for feature in item["matched_features"]:
            if feature.startswith("specific_signs:"):
                reasons.append(f"sinal específico: {prettify_term(feature.split(':', 1)[1])}")
            elif feature.startswith("ai_indicators:"):
                reasons.append(f"indicador forte: {prettify_term(feature.split(':', 1)[1])}")
            elif feature.startswith("visual_characteristics:"):
                reasons.append(f"padrão visual: {prettify_term(feature.split(':', 1)[1])}")
            elif feature.startswith("visual_profile:"):
                parts = feature.split(":", 2)
                reasons.append(f"perfil visual: {prettify_term(parts[-1])}")
            elif feature.startswith("perfil_diferencial:"):
                reasons.append(f"perfil diferencial: {prettify_term(feature.split(':', 1)[1])}")
            elif feature.startswith("diferencial:"):
                parts = feature.split(":", 2)
                reasons.append(f"diferencial contra {prettify_term(parts[1].replace('_', ' '))}: {prettify_term(parts[2])}")
            elif feature.startswith("incomum:"):
                reasons.append(f"achado incomum: {prettify_term(feature.split(':', 1)[1])}")
            elif feature.startswith("local_signs:"):
                reasons.append(f"sinal local: {prettify_term(feature.split(':', 1)[1])}")
            elif feature.startswith("general_signs:"):
                reasons.append(f"sinal geral: {prettify_term(feature.split(':', 1)[1])}")
            elif feature.startswith("sintoma:"):
                reasons.append(prettify_term(feature.split(':', 1)[1]))
            elif feature.startswith("caracteristica:"):
                reasons.append(f"característica da picada: {prettify_term(feature.split(':', 1)[1].replace('_', ' '))}")
            elif feature.startswith("ausencia:"):
                reasons.append(f"ausência compatível: {prettify_term(feature.split(':', 1)[1].replace('_', ' '))}")
            elif feature.startswith("evidencia_negativa:"):
                parts = feature.split(":", 2)
                reasons.append(f"evidencia negativa moderada: {prettify_term(parts[1].replace('_', ' '))}")
            elif feature.startswith("evidencia_contraria:"):
                reasons.append(f"evidencia contraria: {prettify_term(feature.split(':', 1)[1].replace('_', ' '))}")
            elif feature.startswith("estruturado_parcial:"):
                reasons.append(f"sinal parcial: {prettify_term(feature.split(':', 1)[1].replace('_', ' '))}")
            elif feature.startswith("tempo:"):
                reasons.append(f"evolucao temporal: {prettify_term(feature.split(':', 1)[1].replace('_', ' '))}")
            elif feature.startswith("contexto_acidente:"):
                reasons.append(f"contexto do acidente: {prettify_term(feature.split(':', 1)[1].replace('_', ' '))}")
            elif feature.startswith("possivel:"):
                reasons.append(f"característica possível: {prettify_term(feature.split(':', 1)[1].replace('_', ' '))}")
            elif feature.startswith("ambiente:"):
                reasons.append(prettify_term(feature.split(':', 1)[1]))
            elif feature.startswith("local:"):
                reasons.append(prettify_term(feature.split(':', 1)[1]))
            elif feature.startswith("contexto:"):
                reasons.append(prettify_term(feature.split(':', 1)[1]))
            elif feature.startswith("regiao:"):
                reasons.append(f"região {prettify_term(feature.split(':', 1)[1])}")
            elif feature.startswith("conjunto viuva-negra:"):
                reasons.append(prettify_term(feature.replace("conjunto viuva-negra:", "padrao de viuva-negra:")))
            elif feature == "conjunto tipico de viuva-negra":
                reasons.append("conjunto tipico de viuva-negra")
            elif feature.startswith("conjunto surucucu:"):
                reasons.append(prettify_term(feature.replace("conjunto surucucu:", "padrao de surucucu:")))
            elif feature == "conjunto tipico de surucucu":
                reasons.append("conjunto tipico de surucucu")
            elif feature == "nome citado":
                reasons.append("nome citado no relato")

        if not reasons:
            fallback_reasons = []
            for symptom in tokenize_terms(item["symptoms_reference"].split(", ")):
                if symptom and symptom in normalized_report:
                    fallback_reasons.append(prettify_term(symptom))
            if state:
                item_regions = [normalize_text(part.strip()) for part in item["regions"].split(",")]
                if any(region == "todo o brasil" or state_matches_region(state, region) for region in item_regions):
                    fallback_reasons.append(f"região compatível com {state}")
            reasons = fallback_reasons

        reasons = list(dict.fromkeys(reasons))
        item["reasons"] = reasons
        item["reason_text"] = ", ".join(reasons)

    return top_matches


def build_recommendations(species_matches):
    if not species_matches:
        return [
            "Lave o local com água e sabão.",
            "Observe se surgem sintomas importantes como falta de ar, vômito, febre alta ou piora rápida.",
            "Se houver piora importante, procure atendimento médico imediatamente.",
        ]

    top_match = species_matches[0]
    recommendations = [top_match["guidance"]]

    if top_match.get("dont_do"):
        recommendations.append(top_match["dont_do"])

    risk_level = normalize_text(top_match.get("risk_level") or top_match.get("severity"))
    if risk_level in {"alto", "muito alto"} or "grave" in risk_level:
        recommendations.append("Procure consulta médica urgente o quanto antes para avaliação adequada, confirmação do quadro e orientação do tratamento correto.")
    else:
        recommendations.append("Observe a evolução dos sintomas nas próximas horas.")
        recommendations.append("Procure atendimento se houver piora da dor, inchaço, febre ou novos sintomas.")

    return recommendations


URGENT_TRIAGE_TERMS = {
    "falta de ar": ["falta de ar", "dificuldade para respirar", "nao consigo respirar", "nao consegue respirar", "sufocando"],
    "desmaio": ["desmaio", "desmaiei", "desmaiou", "perda de consciencia"],
    "dor intensa": ["dor extrema", "dor insuportavel", "insuportavel"],
    "vomitos intensos": ["vomitos intensos", "vomitando muito", "vomito persistente"],
    "sangramento": ["sangramento intenso", "muito sangue", "sangramento importante"],
    "paralisia": ["paralisia", "nao consigo mexer", "fraqueza intensa"],
    "confusao": ["confusao mental", "confuso", "sonolencia intensa", "muito sonolento"],
}


def has_any_triage_term(report_text, terms):
    normalized = normalize_text(report_text)
    return any(term in normalized for term in terms)


def has_urgent_triage_sign(report_text):
    normalized = normalize_text(report_text)
    for terms in URGENT_TRIAGE_TERMS.values():
        if any(term in normalized for term in terms):
            return True
    return False


def has_pain_intensity(report_text):
    normalized = normalize_text(report_text)
    pain_terms = [
        "dor leve",
        "dor moderada",
        "dor media",
        "dor forte",
        "dor intensa",
        "dor extrema",
        "pouca dor",
        "muita dor",
        "insuportavel",
    ]
    short_intensity_answers = [
        "leve",
        "moderada",
        "media",
        "forte",
        "intensa",
        "extrema",
        "insuportavel",
    ]

    if any(term in normalized for term in pain_terms):
        return True

    if "dor" not in normalized:
        return False

    return any(re.search(rf"\b{re.escape(answer)}\b", normalized) for answer in short_intensity_answers)


def has_time_reference(report_text):
    return has_any_triage_term(
        report_text,
        [
            "minuto",
            "minutos",
            "hora",
            "horas",
            "dia",
            "dias",
            "semana",
            "semanas",
            "ontem",
            "hoje",
            "agora",
        ],
    )


def has_systemic_symptom_answer(report_text):
    return has_any_triage_term(
        report_text,
        [
            "febre",
            "vomito",
            "vomitos",
            "nausea",
            "diarreia",
            "tontura",
            "suor",
            "calafrios",
            "falta de ar",
            "desmaio",
            "nao tive",
            "nao tenho",
            "sem febre",
            "sem vomito",
        ],
    )


def normalize_question_key(value):
    return re.sub(r"[^a-z0-9]+", "", normalize_text(value))


def was_triage_question_asked(report_text, question):
    return normalize_question_key(question) in normalize_question_key(report_text)


def has_pain_start_answer(report_text):
    return has_any_triage_term(
        report_text,
        ["imediatamente", "na hora", "demorou", "depois", "apos", "rapido", "lentamente"],
    )


def has_pain_progression_answer(report_text):
    return has_any_triage_term(
        report_text,
        ["aumentando", "piorando", "melhorando", "igual", "estavel", "mais forte", "menos forte"],
    )


def has_pain_type_answer(report_text):
    return has_any_triage_term(
        report_text,
        ["pontada", "pontadas", "queimacao", "queima", "pressao", "latejando", "latejamento"],
    )


def has_local_appearance_answer(report_text):
    return has_any_triage_term(
        report_text,
        [
            "inchado",
            "inchaco",
            "vermelho",
            "vermelhidao",
            "quente",
            "bolha",
            "roxo",
            "escuro",
            "necrose",
            "sangramento",
            "pus",
            "endurecida",
            "dormente",
            "formigamento",
            "duas marcas",
            "presas",
        ],
    )


def has_emergency_screen_answer(report_text):
    return has_any_triage_term(
        report_text,
        [
            "respira normalmente",
            "respirando normal",
            "consigo respirar",
            "nao consegue respirar",
            "ficar em pe",
            "ficar de pe",
            "desmaio",
            "convulsao",
            "convulsoes",
            "aperto no peito",
            "dificuldade para falar",
            "dificuldade para engolir",
        ],
    )


def has_environment_answer(report_text):
    return has_any_triage_term(
        report_text,
        ["casa", "quintal", "mato", "rio", "plantacao", "galpao", "madeira", "entulho", "pedras", "caixas", "dia", "noite"],
    )


def has_animal_seen_answer(report_text):
    return has_any_triage_term(
        report_text,
        ["vi o animal", "vi a aranha", "vi o escorpiao", "vi a cobra", "nao vi", "foto do animal", "animal foi visto"],
    )


def has_victim_history_answer(report_text):
    return has_any_triage_term(
        report_text,
        ["crianca", "idoso", "gestante", "alergia", "pressao alta", "diabetes", "problema cardiaco", "medicamento", "remedio"],
    )


def count_identification_questions(asked_questions):
    count = 0
    for question_id in asked_questions or []:
        question = QUESTION_BY_ID.get(str(question_id))
        if question and question.get("category") == "differential":
            count += 1
    return count


def profile_detail_count(clinical_profile):
    return sum(
        1
        for entry in (clinical_profile or {}).values()
        if entry.get("confidence", 0) >= CLINICAL_FIELD_CONFIDENCE_THRESHOLD and entry.get("value") != "unknown"
    )


def ranking_is_stable(species_matches):
    if not species_matches:
        return False
    if len(species_matches) == 1:
        return True
    return species_matches[0].get("score", 0) - species_matches[1].get("score", 0) >= 12


def question_has_relevant_top_species(question, top_animals):
    supports = {
        animal
        for animal, weight in (question.get("supports_yes") or {}).items()
        if weight > 0
    }
    if not supports:
        return question.get("category") in {"urgency", "context"}
    return bool(supports.intersection(top_animals))


def estimate_diagnostic_gain(question, top_animals):
    weights = question.get("supports_yes") or {}
    supports_no = question.get("supports_no") or {}
    values = [weights.get(animal, 0.0) - supports_no.get(animal, 0.0) for animal in top_animals]
    if len(values) < 2:
        return question.get("diagnostic_gain", 0)
    spread = max(values) - min(values)
    non_zero = sum(1 for value in values if abs(value) > 0.01)
    discrimination = spread / 8.0
    if non_zero == len(values) and spread < 1.0:
        discrimination *= 0.35
    coverage = non_zero / max(1, len(values))
    base_gain = question.get("diagnostic_gain", 0)
    return min(1.0, max(base_gain * 0.6, discrimination + (coverage * 0.15)))


def estimate_question_time_relevance(question, bite_time):
    minutes = (bite_time or {}).get("minutes")
    if minutes is None:
        return 1.0
    target = question.get("target_field")
    if target in {"blister", "purple_skin"} and minutes < 120:
        return 0.55
    if target == "urine_change" and minutes < 240:
        return 0.45
    if target in {"pain_onset", "swelling_progression", "bleeding"} and minutes < 180:
        return 1.08
    if target in {"blurred_vision", "weakness"} and minutes >= 180:
        return 1.12
    return 1.0


def build_question_selection_log(analysis):
    return {
        "current_ranking": [
            {"animal": item.get("animal"), "score": item.get("score")}
            for item in (analysis.get("species_matches") or [])[:5]
        ],
        "compared_species": [item.get("animal") for item in (analysis.get("species_matches") or [])[:3]],
        "candidates": [],
        "ignored_repetition": [],
        "ignored_answered": [],
        "ignored_low_gain": [],
        "chosen": None,
        "reason": "",
    }


def select_best_triage_question(analysis, question_count=0, max_questions=5, asked_questions=None):
    clinical_profile = analysis.get("clinical_profile") or {}
    asked_questions = asked_questions or []
    asked_set = {normalize_question_key(question) for question in asked_questions}
    top_animals = [item.get("animal") for item in (analysis.get("species_matches") or [])[:3] if item.get("animal")]
    identification_count = count_identification_questions(asked_questions)
    selection_log = build_question_selection_log(analysis)
    bite_time = analysis.get("bite_time_analysis") or bite_time_from_profile_or_report(clinical_profile, analysis.get("report_text") or "")
    best_candidate = None
    best_priority = None

    for question in QUESTION_BANK:
        question_id = question["question_id"]
        normalized_question_id = normalize_question_key(question_id)
        if normalized_question_id in asked_set:
            selection_log["ignored_repetition"].append({"question_id": question_id, "reason": "question_id ja perguntado"})
            continue

        target_fields = question_target_fields(question)
        if clinical_fields_answered(clinical_profile, target_fields):
            selection_log["ignored_answered"].append(
                {"question_id": question_id, "target_field": question.get("target_field"), "reason": "campo clinico ja preenchido"}
            )
            continue

        category = question.get("category")
        if category == "differential" and identification_count >= max_questions:
            selection_log["ignored_low_gain"].append({"question_id": question_id, "reason": "limite de perguntas de identificacao"})
            continue

        if category == "differential" and not question_has_relevant_top_species(question, top_animals):
            selection_log["ignored_low_gain"].append({"question_id": question_id, "reason": "baixo ganho para top 3 atual"})
            continue

        diagnostic_gain = estimate_diagnostic_gain(question, top_animals)
        time_relevance = estimate_question_time_relevance(question, bite_time)
        missing_information_bonus = 0.25 if not clinical_fields_answered(clinical_profile, target_fields, 0.35) else 0
        repetition_penalty = 1.0 if normalized_question_id in asked_set else 0
        already_answered_penalty = 2.0 if clinical_fields_answered(clinical_profile, target_fields) else 0
        priority = (diagnostic_gain * time_relevance) + question.get("urgency_priority", 0) + missing_information_bonus - repetition_penalty - already_answered_penalty
        candidate_log = {
            "question_id": question_id,
            "target_field": question.get("target_field"),
            "category": category,
            "diagnostic_gain": round(diagnostic_gain, 2),
            "time_relevance": round(time_relevance, 2),
            "priority": round(priority, 2),
        }
        selection_log["candidates"].append(candidate_log)

        if category != "urgency" and priority < MIN_DIAGNOSTIC_PRIORITY:
            selection_log["ignored_low_gain"].append({"question_id": question_id, "priority": round(priority, 2), "reason": "prioridade diagnostica baixa"})
            continue

        if best_candidate is None or priority > best_priority:
            best_candidate = dict(question)
            best_candidate["priority"] = round(priority, 2)
            best_candidate["diagnostic_gain"] = round(diagnostic_gain, 2)
            best_priority = priority

    if best_candidate:
        selection_log["chosen"] = {
            "question_id": best_candidate["question_id"],
            "target_field": best_candidate.get("target_field"),
            "priority": best_candidate.get("priority"),
        }
        selection_log["reason"] = "maior prioridade combinando urgencia, ganho diagnostico e informacao ausente"

    analysis["question_selection_log"] = selection_log
    return best_candidate


def build_triage_candidate(question_id, text, options=None, priority=50, answer_type="text"):
    return {
        "id": question_id,
        "text": text,
        "options": options or [],
        "priority": priority,
        "answer_type": answer_type,
    }


YES_NO_UNKNOWN_OPTIONS = ["Sim", "Não", "Não sei"]


SPECIES_TRIAGE_QUESTIONS = {
    "aranha_marrom": [
        ("dor_lenta", "A dor era fraca no início e aumentou algumas horas depois?", "dor fraca no inicio e aumentou depois", "sem dor fraca inicial que aumentou depois"),
        ("arroxeado", "O local está ficando arroxeado, escuro ou com aparência de hematoma?", "local arroxeado escuro com hematoma", "sem local arroxeado escuro ou hematoma"),
        ("bolha", "Apareceu alguma bolha no centro ou ao redor da picada?", "bolha no centro ou ao redor da picada", "sem bolha no centro ou ao redor da picada"),
        ("area_aumentando", "A área afetada está aumentando lentamente desde o acidente?", "area afetada aumentando lentamente", "area afetada nao esta aumentando lentamente"),
        ("sistemicos", "Você apresentou febre, mal-estar, náusea ou urina mais escura?", "febre mal-estar nausea ou urina escura", "sem febre mal-estar nausea ou urina escura"),
    ],
    "armadeira": [
        ("dor_imediata", "A dor começou imediatamente e ficou muito intensa?", "dor imediata muito intensa", "sem dor imediata muito intensa"),
        ("dor_espalhou", "A dor se espalhou para outras partes do membro ou do corpo?", "dor irradiando ou se espalhando", "dor nao irradiou nem se espalhou"),
        ("autonomicos", "Você apresentou suor intenso, agitação ou tremores?", "suor intenso agitacao ou tremores", "sem suor intenso agitacao ou tremores"),
        ("nausea_saliva", "Você teve náusea, vômito ou aumento da salivação?", "nausea vomito ou salivacao aumentada", "sem nausea vomito ou salivacao aumentada"),
        ("contexto", "O acidente aconteceu ao mexer em calçados, roupas, caixas ou cachos de banana?", "acidente em calcados roupas caixas ou cachos de banana", "sem contexto de calcados roupas caixas ou cachos de banana"),
    ],
    "viuva_negra": [
        ("queimacao", "A picada causou ardência ou sensação de queimação?", "ardencia ou queimacao", "sem ardencia ou queimacao"),
        ("espasmos", "Você está sentindo contrações, tremores ou espasmos musculares?", "contracoes tremores ou espasmos musculares", "sem contracoes tremores ou espasmos musculares"),
        ("abdomen", "O abdômen está dolorido, rígido ou contraído?", "dor abdominal rigidez abdominal ou abdomen contraido", "sem dor abdominal rigidez abdominal ou abdomen contraido"),
        ("autonomicos", "Você apresentou suor intenso, ansiedade ou agitação?", "suor intenso ansiedade ou agitacao", "sem suor intenso ansiedade ou agitacao"),
        ("dor_espalhou", "A dor começou no local e depois se espalhou pelo corpo?", "dor comecou no local e espalhou pelo corpo", "dor nao se espalhou pelo corpo"),
    ],
    "escorpiao_amarelo": [
        ("dor_queimacao", "A dor e a queimação começaram imediatamente após a picada?", "dor e queimacao imediatas", "sem dor e queimacao imediatas"),
        ("sistemicos", "Você apresentou suor intenso, náusea ou vômitos?", "suor intenso nausea ou vomitos", "sem suor intenso nausea ou vomitos"),
        ("salivacao", "Está salivando mais que o normal?", "salivacao aumentada", "sem salivacao aumentada"),
        ("cardiorrespiratorio", "Você sente o coração acelerado, falta de ar ou muita agitação?", "coracao acelerado falta de ar ou muita agitacao", "sem coracao acelerado falta de ar ou muita agitacao"),
        ("risco_vitima", "A pessoa picada é criança, idosa ou possui alguma condição de saúde importante?", "crianca idoso ou condicao de saude importante", "nao e crianca idoso e sem condicao de saude importante"),
    ],
    "escorpiao_marrom": [
        ("dor_formigamento", "A picada provocou dor imediata, queimação ou formigamento?", "dor imediata queimacao ou formigamento", "sem dor imediata queimacao ou formigamento"),
        ("local", "Existe vermelhidão ou pequeno inchaço no local?", "vermelhidao ou pequeno inchaco local", "sem vermelhidao ou pequeno inchaco local"),
        ("sistemicos", "Você apresentou náusea, vômito, suor ou agitação?", "nausea vomito suor ou agitacao", "sem nausea vomito suor ou agitacao"),
        ("contexto", "O acidente aconteceu dentro de casa, próximo a entulhos, madeira, ralos ou materiais de construção?", "dentro de casa entulho madeira ralo ou material de construcao", "sem contexto de casa entulho madeira ralo ou material de construcao"),
        ("foto_cor", "Você conseguiu observar ou fotografar a cor e o formato do escorpião?", "observou ou fotografou cor e formato do escorpiao", "nao observou nem fotografou o escorpiao"),
    ],
    "jararaca": [
        ("inchaco_dor", "O local começou a inchar e doer pouco tempo depois da mordida?", "inchaco e dor pouco tempo depois da mordida", "sem inchaco e dor pouco tempo depois da mordida"),
        ("inchaco_subindo", "O inchaço está aumentando ou subindo pelo membro?", "inchaco aumentando ou subindo pelo membro", "inchaco nao esta aumentando ou subindo"),
        ("sangramento_local", "Existe sangramento no local da mordida?", "sangramento no local da mordida", "sem sangramento no local da mordida"),
        ("sangramento_geral", "Você apresentou sangramento na gengiva, no nariz ou na urina?", "sangramento na gengiva nariz ou urina", "sem sangramento na gengiva nariz ou urina"),
        ("pele_roxa", "A pele está ficando arroxeada, com bolhas ou áreas escurecidas?", "pele arroxeada bolhas ou areas escurecidas", "sem pele arroxeada bolhas ou areas escurecidas"),
    ],
    "cascavel": [
        ("pouco_local", "A dor e o inchaço no local são pequenos ou quase inexistentes?", "pouca dor pouco inchaco ou pouca lesao local", "dor ou inchaco local importante"),
        ("palpebras", "Suas pálpebras estão caídas ou você está com dificuldade para manter os olhos abertos?", "palpebras caidas ou dificuldade para manter olhos abertos", "sem palpebras caidas ou dificuldade nos olhos"),
        ("visao", "Você está com visão dupla ou visão embaçada?", "visao dupla ou visao embacada", "sem visao dupla ou embacada"),
        ("fraqueza", "Está sentindo fraqueza muscular, dificuldade para caminhar ou falar?", "fraqueza muscular dificuldade para caminhar ou falar", "sem fraqueza muscular dificuldade para caminhar ou falar"),
        ("urina", "Sua urina ficou escura, avermelhada ou com aparência diferente?", "urina escura avermelhada ou diferente", "urina sem alteracao"),
    ],
    "coral_verdadeira": [
        ("palpebras", "Você está com dificuldade para abrir os olhos ou com as pálpebras caídas?", "dificuldade para abrir olhos ou palpebras caidas", "sem dificuldade para abrir olhos ou palpebras caidas"),
        ("visao", "Está com visão dupla ou dificuldade para focalizar?", "visao dupla ou dificuldade para focalizar", "sem visao dupla ou dificuldade para focalizar"),
        ("fala_engolir", "Você sente dificuldade para falar, engolir ou movimentar a língua?", "dificuldade para falar engolir ou movimentar a lingua", "sem dificuldade para falar engolir ou movimentar a lingua"),
        ("fraqueza_respirar", "Está sentindo fraqueza muscular ou dificuldade para respirar?", "fraqueza muscular ou dificuldade para respirar", "sem fraqueza muscular ou dificuldade para respirar"),
        ("pouco_local", "A mordida apresentou pouca dor ou poucos sinais no local, apesar dos outros sintomas?", "pouca dor ou poucos sinais no local", "dor ou sinais locais importantes"),
    ],
    "surucucu": [
        ("floresta", "O acidente aconteceu em mata fechada ou região de floresta?", "mata fechada ou regiao de floresta", "nao aconteceu em mata fechada ou floresta"),
        ("dor_inchaco", "O local apresenta dor forte e inchaço que está aumentando?", "dor forte e inchaco aumentando", "sem dor forte e inchaco aumentando"),
        ("sangramento", "Houve sangramento no local, na gengiva, no nariz ou em outra região?", "sangramento local gengiva nariz ou outra regiao", "sem sangramento local gengiva nariz ou outra regiao"),
        ("gastro", "Você apresentou diarreia, cólicas, náusea ou vômitos?", "diarreia colicas nausea ou vomitos", "sem diarreia colicas nausea ou vomitos"),
        ("vagal", "Você apresentou tontura, sensação de desmaio, pressão baixa ou batimentos mais lentos?", "tontura desmaio pressao baixa ou batimentos lentos", "sem tontura desmaio pressao baixa ou batimentos lentos"),
    ],
}


def get_species_triage_question(question_id):
    for animal, questions in SPECIES_TRIAGE_QUESTIONS.items():
        for suffix, text, positive_evidence, negative_evidence in questions:
            if question_id == f"species_{animal}_{suffix}":
                return {
                    "animal": animal,
                    "suffix": suffix,
                    "text": text,
                    "positive_evidence": positive_evidence,
                    "negative_evidence": negative_evidence,
                }
    return None


def build_species_triage_candidates(analysis, asked_question_keys):
    candidates = []
    species_matches = analysis.get("species_matches") or []

    for species_index, match in enumerate(species_matches[:3]):
        animal = match.get("animal")
        questions = SPECIES_TRIAGE_QUESTIONS.get(animal) or []
        if not questions:
            continue

        asked_for_animal = sum(1 for key in asked_question_keys if key.startswith(normalize_question_key(f"species_{animal}_")))
        if asked_for_animal >= 2:
            continue

        for question_index, (suffix, text, _positive_evidence, _negative_evidence) in enumerate(questions):
            question_id = f"species_{animal}_{suffix}"
            if normalize_question_key(question_id) in asked_question_keys:
                continue

            candidates.append(build_triage_candidate(
                question_id,
                text,
                YES_NO_UNKNOWN_OPTIONS,
                priority=8 + (species_index * 20) + question_index,
                answer_type="single_choice",
            ))
            break

    return candidates


def describe_triage_answer(question_id, answer):
    question = QUESTION_BY_ID.get(question_id or "")
    if question:
        return clinical_answer_marker(question, answer)

    question = get_species_triage_question(question_id or "")
    if not question:
        return ""

    normalized_answer = normalize_text(answer)
    if not normalized_answer or "nao sei" in normalized_answer:
        return ""
    if normalized_answer.startswith("sim"):
        return f"resposta a favor de {question['animal']}: {question['positive_evidence']}"
    if normalized_answer.startswith("nao") or normalized_answer.startswith("não"):
        return f"resposta contra {question['animal']}: {question['negative_evidence']}"
    return ""


def get_triage_question_candidates(analysis):
    report_text = analysis.get("report_text") or ""
    symptoms = analysis.get("symptoms") or []
    has_pain = "dor" in symptoms or "dor" in normalize_text(report_text)
    candidates = []
    asked_question_keys = {
        normalize_question_key(question)
        for question in analysis.get("asked_questions", [])
    }

    if not has_emergency_screen_answer(report_text):
        candidates.append(build_triage_candidate(
            "emergency_screen",
            "A vítima consegue respirar normalmente e ficar em pé?",
            ["Sim, respira e fica em pé", "Não respira bem", "Desmaiou ou está muito fraca"],
            priority=5,
            answer_type="single_choice",
        ))

    candidates.extend(build_species_triage_candidates(analysis, asked_question_keys))

    if not symptoms:
        candidates.append(build_triage_candidate(
            "current_symptoms",
            "Quais sintomas você está sentindo agora? Por exemplo: dor, coceira, inchaço, vermelhidão, náusea ou falta de ar.",
            ["Dor e inchaço", "Coceira e vermelhidão", "Náusea, tontura ou falta de ar"],
            priority=10,
        ))

    if has_pain and not has_pain_intensity(report_text):
        candidates.append(build_triage_candidate(
            "pain_intensity",
            "A dor é leve, moderada ou intensa?",
            ["Leve", "Moderada", "Intensa ou insuportável"],
            priority=15,
            answer_type="single_choice",
        ))

    if has_pain and not has_pain_start_answer(report_text):
        candidates.append(build_triage_candidate(
            "pain_start",
            "A dor começou imediatamente ou demorou para aparecer?",
            ["Imediatamente", "Demorou minutos ou horas", "Não sei"],
            priority=25,
            answer_type="single_choice",
        ))

    if has_pain and not has_pain_progression_answer(report_text):
        candidates.append(build_triage_candidate(
            "pain_progression",
            "A dor está aumentando com o tempo?",
            ["Está aumentando", "Está igual", "Está melhorando"],
            priority=30,
            answer_type="single_choice",
        ))

    if has_pain and not has_pain_type_answer(report_text):
        candidates.append(build_triage_candidate(
            "pain_type",
            "A dor é em pontadas, queimação, pressão ou latejamento?",
            ["Pontadas", "Queimação", "Pressão ou latejamento"],
            priority=35,
            answer_type="single_choice",
        ))

    if not analysis.get("bite_location"):
        candidates.append(build_triage_candidate(
            "bite_location",
            "Em qual parte do corpo aconteceu?",
            ["Mão ou braço", "Pé ou perna", "Rosto, pescoço ou tronco"],
            priority=20,
        ))

    if not has_local_appearance_answer(report_text):
        candidates.append(build_triage_candidate(
            "local_appearance",
            "O local está inchado, vermelho, quente, com bolha, roxo, escuro, com pus ou sangrando?",
            ["Inchado ou vermelho", "Bolha, roxo ou escuro", "Pus ou sangramento"],
            priority=40,
        ))

    if not has_time_reference(report_text):
        candidates.append(build_triage_candidate(
            "bite_time",
            "Quanto tempo faz desde o acidente?",
            ["Menos de 1 hora", "1 a 6 horas", "Mais de 6 horas"],
            priority=18,
        ))

    if not has_systemic_symptom_answer(report_text):
        candidates.append(build_triage_candidate(
            "systemic_symptoms",
            "Teve febre, vômito, diarreia, náusea, tontura, suor intenso, tremores ou falta de ar?",
            ["Não tive esses sintomas", "Náusea, tontura ou suor", "Febre, vômito, tremores ou falta de ar"],
            priority=12,
        ))

    if not has_environment_answer(report_text):
        candidates.append(build_triage_candidate(
            "environment",
            "O acidente aconteceu em casa, quintal, mato, rio, plantação ou galpão?",
            ["Dentro de casa", "Quintal ou galpão", "Mato, rio ou plantação"],
            priority=55,
        ))

    if not has_animal_seen_answer(report_text):
        candidates.append(build_triage_candidate(
            "animal_seen",
            "O animal foi visto ou o usuário conseguiu tirar foto dele?",
            ["Vi o animal", "Tenho foto", "Não vi o animal"],
            priority=50,
            answer_type="single_choice",
        ))

    if not has_victim_history_answer(report_text):
        candidates.append(build_triage_candidate(
            "victim_history",
            "A vítima é criança, idosa, gestante, tem alergias ou usa algum medicamento contínuo?",
            ["Não", "Criança, idosa ou gestante", "Tem alergia ou usa medicamento"],
            priority=60,
        ))

    return sorted(candidates, key=lambda item: (item["priority"], item["id"]))


def build_triage_question_payload(analysis, question_count=0, max_questions=5, asked_questions=None):
    asked_questions = asked_questions or []
    asked_set = {normalize_question_key(item) for item in asked_questions}
    clinical_profile = analysis.get("clinical_profile") or {}
    species_matches = analysis.get("species_matches") or []
    identification_count = count_identification_questions(asked_questions)
    urgent_unanswered = any(
        question.get("category") == "urgency"
        and normalize_question_key(question["question_id"]) not in asked_set
        and not clinical_fields_answered(clinical_profile, question_target_fields(question))
        for question in QUESTION_BANK
    )

    if (
        not urgent_unanswered
        and identification_count > 0
        and (
            profile_detail_count(clinical_profile) >= 8
            or ranking_is_stable(species_matches)
            or identification_count >= max_questions
        )
    ):
        analysis["question_selection_log"] = build_question_selection_log(analysis)
        analysis["question_selection_log"]["reason"] = "parada antecipada por informacoes suficientes, ranking estavel ou limite de identificacao"
        return None

    candidate = select_best_triage_question(
        analysis,
        question_count=question_count,
        max_questions=max_questions,
        asked_questions=asked_questions,
    )
    if not candidate:
        return None

    return {
        "id": candidate["question_id"],
        "question_id": candidate["question_id"],
        "target_field": candidate.get("target_field"),
        "category": candidate.get("category"),
        "text": candidate["text"],
        "options": candidate.get("options", []),
        "priority": candidate.get("priority", 0),
        "diagnostic_gain": candidate.get("diagnostic_gain", 0),
        "answer_type": candidate.get("answer_type", "text"),
    }


def build_triage_question(analysis, question_count=0, max_questions=5, asked_questions=None):
    payload = build_triage_question_payload(
        analysis,
        question_count=question_count,
        max_questions=max_questions,
        asked_questions=asked_questions,
    )
    return payload["text"] if payload else None


def analyze_report(report_text):
    report_text = report_text or ""
    state = extract_state(report_text)
    city = extract_city(report_text, state=state)
    region = extract_region(report_text, state=state)
    clinical_profile = extract_structured_clinical_data(report_text)
    bite_time_analysis = bite_time_from_profile_or_report(clinical_profile, report_text)
    symptoms = extract_symptoms(report_text)
    bite_location = clinical_field_value(clinical_profile, "bite_location") or extract_bite_location(report_text)
    bug_matches = rank_possible_bugs(report_text)
    species_matches = rank_specific_species(report_text, state=state, clinical_profile=clinical_profile)
    recommendations = build_recommendations(species_matches)
    urgent_triage = has_urgent_triage_sign(report_text)

    if urgent_triage:
        recommendations.insert(
            0,
            "Procure atendimento médico imediatamente, porque o relato contém sinal de alerta importante.",
        )

    return {
        "report_text": report_text,
        "symptoms": symptoms,
        "city": city,
        "state": state,
        "region": region,
        "bite_location": BITE_LOCATION_LABELS.get(bite_location, bite_location),
        "clinical_profile": clinical_profile,
        "bite_time_analysis": bite_time_analysis,
        "bug_matches": bug_matches,
        "species_matches": species_matches,
        "recommendations": recommendations,
        "urgent_triage": urgent_triage,
        "question_selection_log": build_question_selection_log({"species_matches": species_matches}),
    }

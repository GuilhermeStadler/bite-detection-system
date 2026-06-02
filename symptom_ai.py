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


def normalize_text(value):
    value = value or ""
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    ascii_value = ascii_value.lower()
    return re.sub(r"\s+", " ", ascii_value).strip()


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


def rank_specific_species(report_text, state=None):
    normalized_report = normalize_text(report_text)
    ranked = []
    detected_region = extract_region(report_text, state=state)

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


def get_triage_question_candidates(analysis):
    report_text = analysis.get("report_text") or ""
    symptoms = analysis.get("symptoms") or []
    has_pain = "dor" in symptoms or "dor" in normalize_text(report_text)
    candidates = []

    if not symptoms:
        candidates.append("Quais sintomas você está sentindo agora? Por exemplo: dor, coceira, inchaço, vermelhidão, náusea ou falta de ar.")

    if has_pain and not has_pain_intensity(report_text):
        candidates.append("A dor é leve, moderada ou intensa?")

    if not has_emergency_screen_answer(report_text):
        candidates.append("A vítima consegue respirar normalmente e ficar em pé?")

    if has_pain and not has_pain_start_answer(report_text):
        candidates.append("A dor começou imediatamente ou demorou para aparecer?")

    if has_pain and not has_pain_progression_answer(report_text):
        candidates.append("A dor está aumentando com o tempo?")

    if has_pain and not has_pain_type_answer(report_text):
        candidates.append("A dor é em pontadas, queimação, pressão ou latejamento?")

    if not analysis.get("bite_location"):
        candidates.append("Em qual parte do corpo aconteceu?")

    if not has_local_appearance_answer(report_text):
        candidates.append("O local está inchado, vermelho, quente, com bolha, roxo, escuro, com pus ou sangrando?")

    if not has_time_reference(report_text):
        candidates.append("Quanto tempo faz desde o acidente?")

    if not has_systemic_symptom_answer(report_text):
        candidates.append("Teve febre, vômito, diarreia, náusea, tontura, suor intenso, tremores ou falta de ar?")

    if not has_environment_answer(report_text):
        candidates.append("O acidente aconteceu em casa, quintal, mato, rio, plantação ou galpão?")

    if not has_animal_seen_answer(report_text):
        candidates.append("O animal foi visto ou o usuário conseguiu tirar foto dele?")

    if not has_victim_history_answer(report_text):
        candidates.append("A vítima é criança, idosa, gestante, tem alergias ou usa algum medicamento contínuo?")

    return candidates


def build_triage_question(analysis, question_count=0, max_questions=5, asked_questions=None):
    if question_count >= max_questions:
        return None

    report_text = analysis.get("report_text") or ""
    asked_question_keys = {
        normalize_question_key(question)
        for question in (asked_questions or [])
    }

    if has_urgent_triage_sign(report_text):
        return None

    for question in get_triage_question_candidates(analysis):
        question_key = normalize_question_key(question)
        if question_key not in asked_question_keys and not was_triage_question_asked(report_text, question):
            return question

    return None


def analyze_report(report_text):
    report_text = report_text or ""
    state = extract_state(report_text)
    city = extract_city(report_text, state=state)
    region = extract_region(report_text, state=state)
    symptoms = extract_symptoms(report_text)
    bite_location = extract_bite_location(report_text)
    bug_matches = rank_possible_bugs(report_text)
    species_matches = rank_specific_species(report_text, state=state)
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
        "bug_matches": bug_matches,
        "species_matches": species_matches,
        "recommendations": recommendations,
        "urgent_triage": urgent_triage,
    }

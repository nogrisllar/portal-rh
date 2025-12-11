import bcrypt
# Veja como a importação ficou simples (sem 'src.')
from database import SessionLocal, Usuario

def validar_usuario(username, senha_digitada):
    db = SessionLocal()
    try:
        user = db.query(Usuario).filter(Usuario.username == username).first()
        if not user:
            return None
        
        # Verifica a senha
        if bcrypt.checkpw(senha_digitada.encode('utf-8'), user.senha_hash.encode('utf-8')):
            return user
        else:
            return None
    except Exception as e:
        print(f"Erro de Auth: {e}")
        return None
    finally:
        db.close()
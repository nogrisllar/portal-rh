import sqlalchemy
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
import os

# --- Configuração Simples ---
# O banco será criado na mesma pasta dos arquivos
NOME_BANCO = "sistema.db"
DATABASE_URL = f"sqlite:///{NOME_BANCO}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Tabelas ---
class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False) # CPF
    nome_completo = Column(String, nullable=False)
    senha_hash = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)
    documentos = relationship("Documento", back_populates="dono")

class Documento(Base):
    __tablename__ = "documentos"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    mes_ano = Column(String, nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    dono = relationship("Usuario", back_populates="documentos")

# --- Função de Inicialização ---
def init_db():
    Base.metadata.create_all(bind=engine)
    print(f"--- BANCO DE DADOS '{NOME_BANCO}' CRIADO/ATUALIZADO COM SUCESSO ---")

if __name__ == "__main__":
    init_db()
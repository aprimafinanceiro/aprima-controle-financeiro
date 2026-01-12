-- Script SQL para criar a tabela de imóveis no Supabase
-- Execute este script no SQL Editor do seu projeto Supabase

-- Criar a tabela imoveis
CREATE TABLE IF NOT EXISTS imoveis (
    id BIGSERIAL PRIMARY KEY,
    whatsapp_message_id TEXT,
    whatsapp_from TEXT,
    titulo TEXT NOT NULL,
    descricao TEXT,
    preco TEXT,
    tipo_imovel TEXT,
    imagens_urls JSONB DEFAULT '[]'::jsonb,
    facebook_listing_id TEXT,
    status TEXT DEFAULT 'pendente',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Criar índices para melhorar performance
CREATE INDEX IF NOT EXISTS idx_imoveis_status ON imoveis(status);
CREATE INDEX IF NOT EXISTS idx_imoveis_created_at ON imoveis(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_imoveis_whatsapp_message_id ON imoveis(whatsapp_message_id);
CREATE INDEX IF NOT EXISTS idx_imoveis_facebook_listing_id ON imoveis(facebook_listing_id);

-- Criar função para atualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Criar trigger para atualizar updated_at
CREATE TRIGGER update_imoveis_updated_at
    BEFORE UPDATE ON imoveis
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Habilitar Row Level Security (RLS)
ALTER TABLE imoveis ENABLE ROW LEVEL SECURITY;

-- Criar política para permitir leitura para todos (authenticated users)
CREATE POLICY "Permitir leitura para usuários autenticados"
    ON imoveis FOR SELECT
    USING (auth.role() = 'authenticated' OR auth.role() = 'anon');

-- Criar política para permitir inserção para service_role
CREATE POLICY "Permitir inserção para service role"
    ON imoveis FOR INSERT
    WITH CHECK (true);

-- Criar política para permitir atualização para service_role
CREATE POLICY "Permitir atualização para service role"
    ON imoveis FOR UPDATE
    USING (true)
    WITH CHECK (true);

-- Comentários nas colunas
COMMENT ON TABLE imoveis IS 'Tabela que armazena informações de imóveis recebidos via WhatsApp e publicados no Facebook Marketplace';
COMMENT ON COLUMN imoveis.whatsapp_message_id IS 'ID da mensagem no WhatsApp';
COMMENT ON COLUMN imoveis.whatsapp_from IS 'Número do remetente no WhatsApp';
COMMENT ON COLUMN imoveis.titulo IS 'Título do anúncio gerado automaticamente';
COMMENT ON COLUMN imoveis.descricao IS 'Descrição completa do imóvel';
COMMENT ON COLUMN imoveis.preco IS 'Preço do imóvel extraído da mensagem';
COMMENT ON COLUMN imoveis.tipo_imovel IS 'Tipo: casa, apartamento, kitnet, terreno, comercial';
COMMENT ON COLUMN imoveis.imagens_urls IS 'Array JSON com URLs das imagens';
COMMENT ON COLUMN imoveis.facebook_listing_id IS 'ID do anúncio criado no Facebook Marketplace';
COMMENT ON COLUMN imoveis.status IS 'Status: pendente, publicado, erro';
COMMENT ON COLUMN imoveis.created_at IS 'Data e hora de criação do registro';
COMMENT ON COLUMN imoveis.updated_at IS 'Data e hora da última atualização';
